import numpy as np
from sentence_transformers import SentenceTransformer
import ollama
from tqdm import tqdm

class SemanticComparator:
    def __init__(self, model_name="all-MiniLM-L6-v2", llm_model="gemma3:4b"):
        self.embedder = SentenceTransformer(model_name)
        self.llm_model = llm_model
        self.similarity_threshold = 0.85
        self.max_llm_calls = 50        # cap LLM calls — top 50 most changed
        self.batch_size = 512          # process similarity in batches

    def _normalize(self, emb: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        return emb / np.clip(norms, 1e-10, None)

    def compare(self, chunks_v1: list, chunks_v2: list) -> dict:
        results = { "additions": [], "deletions": [], "updates": [] }

        texts_v1 = [c["content"] for c in chunks_v1]
        texts_v2 = [c["content"] for c in chunks_v2]

        # --- Step 1: Encode ---
        print("   Encoding v1...")
        emb_v1 = self._normalize(
            self.embedder.encode(texts_v1, 
                                 show_progress_bar=True, 
                                 batch_size=64)
        )
        print("   Encoding v2...")
        emb_v2 = self._normalize(
            self.embedder.encode(texts_v2, 
                                 show_progress_bar=True, 
                                 batch_size=64)
        )

        # --- Step 2: Batched similarity (avoids huge matrix in memory) ---
        print("   Computing similarity in batches...")
        matched_v1 = set()
        matched_v2 = set()
        pending_updates = []  # collect updates before LLM calls

        for batch_start in tqdm(range(0, len(emb_v2), self.batch_size),
                                desc="   Comparing batches"):

            batch_end = min(batch_start + self.batch_size, len(emb_v2))
            batch_emb_v2 = emb_v2[batch_start:batch_end]

            # Shape: (batch_size, len_v1)
            sim_batch = np.dot(batch_emb_v2, emb_v1.T)

            for local_idx in range(len(batch_emb_v2)):
                v2_idx = batch_start + local_idx
                best_v1_idx = int(np.argmax(sim_batch[local_idx]))
                best_score = float(sim_batch[local_idx][best_v1_idx])

                if best_score >= self.similarity_threshold:
                    matched_v1.add(best_v1_idx)
                    matched_v2.add(v2_idx)

                    if best_score < 0.98:
                        # Queue update — attach score to prioritize later
                        pending_updates.append({
                            "score": best_score,
                            "v1_idx": best_v1_idx,
                            "v2_idx": v2_idx
                        })
                else:
                    matched_v2.add(v2_idx)
                    results["additions"].append({
                        "section": chunks_v2[v2_idx]["section"],
                        "content": chunks_v2[v2_idx]["content"]
                    })

        # Unmatched v1 → deletions
        for v1_idx, chunk in enumerate(chunks_v1):
            if v1_idx not in matched_v1:
                results["deletions"].append({
                    "section": chunk["section"],
                    "content": chunk["content"]
                })

        # --- Step 3: LLM calls — only for top N most changed ---
        # Sort by score ascending = most changed first
        pending_updates.sort(key=lambda x: x["score"])
        top_updates = pending_updates[:self.max_llm_calls]
        skipped = len(pending_updates) - len(top_updates)

        print(f"\n   Found {len(pending_updates)} updates — "
              f"running LLM on top {len(top_updates)} most changed "
              f"({skipped} flagged without LLM explanation)")

        for item in tqdm(top_updates, desc="   LLM semantic diff"):
            c_v1 = chunks_v1[item["v1_idx"]]
            c_v2 = chunks_v2[item["v2_idx"]]
            semantic_diff = self._get_semantic_diff(
                c_v1["content"], c_v2["content"], c_v1["section"]
            )
            results["updates"].append({
                "section": c_v1["section"],
                "old_content": c_v1["content"],
                "new_content": c_v2["content"],
                "semantic_diff": semantic_diff,
                "similarity_score": round(item["score"], 4)
            })

        # Remaining updates — flagged without LLM explanation
        for item in pending_updates[self.max_llm_calls:]:
            c_v1 = chunks_v1[item["v1_idx"]]
            c_v2 = chunks_v2[item["v2_idx"]]
            results["updates"].append({
                "section": c_v1["section"],
                "old_content": c_v1["content"],
                "new_content": c_v2["content"],
                "semantic_diff": "⚠️ Flagged for manual review — "
                                 "LLM explanation skipped (bulk limit reached)",
                "similarity_score": round(item["score"], 4)
            })

        print(f"\n   ✅ Additions: {len(results['additions'])} | "
              f"Updates: {len(results['updates'])} | "
              f"Deletions: {len(results['deletions'])}")

        return results

    def _get_semantic_diff(self, old: str, new: str, section: str) -> str:
        try:
            prompt = f"""Policy section "{section}" changed.

OLD: {old[:500]}
NEW: {new[:500]}

In under 80 words explain:
1. What specifically changed?
2. What is the intent difference?"""

            response = ollama.chat(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                options={"num_predict": 150}   # limit response length
            )
            return response["message"]["content"]
        except Exception as e:
            return f"LLM error: {str(e)}"