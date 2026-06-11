import ollama
import re
from tqdm import tqdm

def _truncate(text: str, max_chars: int = 600) -> str:
    """Truncate long content for display — keep it readable."""
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "… [truncated]"
        
class RiskAnalyzer:
    def __init__(self, llm_model="gemma3:4b"):
        self.llm_model = llm_model
        self.max_llm_calls = 30        # only LLM on top 30 high-priority changes
        self.max_content_len = 400     # truncate content sent to LLM

        # Rule-based high risk keywords — instant flag without LLM
        self.critical_keywords = [
            "penalty", "fine", "imprisonment", "liable", "criminal",
            "terminate", "revoke", "suspend", "cancel", "forfeit",
            "mandatory", "prohibited", "illegal", "violation", "breach",
            "crore", "lakh", "million", "billion", "%", "deadline",
            "compliance", "tax rate", "interest rate", "surcharge"
        ]
        self.high_keywords = [
            "must", "shall", "required", "obligation", "effective from",
            "amended", "replaced", "deleted", "inserted", "substituted",
            "notice period", "due date", "limit", "threshold", "ceiling"
        ]
        self.low_keywords = [
            "clarif", "example", "illustration", "note:", "explanation",
            "refer to", "see also", "i.e.", "e.g.", "definition"
        ]

    def analyze(self, diff_results: dict) -> list:
        all_changes = (
            [("addition", c) for c in diff_results["additions"]] +
            [("deletion", c) for c in diff_results["deletions"]] +
            [("update",   c) for c in diff_results["updates"]]
        )

        print(f"   Total changes to analyze: {len(all_changes)}")

        # --- Step 1: Rule-based fast scoring for ALL changes ---
        print("   Running rule-based risk filter...")
        pre_scored = []
        for change_type, change in tqdm(all_changes, desc="   Pre-scoring"):
            content = change.get("new_content") or change.get("content", "")
            section = change.get("section", "")
            rule_level = self._rule_based_risk(content, section, change_type)
            pre_scored.append({
                "change_type": change_type,
                "change": change,
                "rule_level": rule_level
            })

        # --- Step 2: Separate by rule-based priority ---
        critical_high = [p for p in pre_scored 
                         if p["rule_level"] in ("critical", "high")]
        medium        = [p for p in pre_scored 
                         if p["rule_level"] == "medium"]
        low_none      = [p for p in pre_scored 
                         if p["rule_level"] in ("low", "none")]

        print(f"   Rule-based → Critical/High: {len(critical_high)} | "
              f"Medium: {len(medium)} | Low/None: {len(low_none)}")

        risks = []

        # --- Step 3: LLM only on top critical/high (capped) ---
        llm_candidates = critical_high[:self.max_llm_calls]
        skipped_llm    = critical_high[self.max_llm_calls:]

        if llm_candidates:
            print(f"   Running LLM on top {len(llm_candidates)} "
                  f"critical/high changes...")
            for item in tqdm(llm_candidates, desc="   LLM risk analysis"):
                risk = self._llm_assess(
                    item["change_type"],
                    item["change"],
                )
                if risk["level"] != "none":
                    risks.append(self._build_risk(
                        item["change"], item["change_type"], risk
                    ))

        # --- Step 4: Rule-based result for everything else ---
        for item in tqdm(skipped_llm + medium, 
                         desc="   Rule-based flagging"):
            if item["rule_level"] != "none":
                risks.append(self._build_risk(
                    item["change"],
                    item["change_type"],
                    {
                        "level": item["rule_level"],
                        "reason": self._rule_reason(
                            item["change"].get("new_content") or 
                            item["change"].get("content", ""),
                            item["rule_level"]
                        ),
                        "recommendation": self._rule_recommendation(
                            item["rule_level"]
                        )
                    }
                ))

        # Low/none — skip entirely (not worth reporting)
        print(f"   Skipped {len(low_none)} low/no-risk changes")

        # Sort by severity
        level_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        risks.sort(key=lambda x: level_order.get(x["risk_level"], 4))

        print(f"\n   ✅ Total risks flagged: {len(risks)}")
        return risks

    # ------------------------------------------------------------------
    # Rule-based risk scoring — instant, no LLM
    # ------------------------------------------------------------------
    def _rule_based_risk(self, content: str, section: str, 
                         change_type: str) -> str:
        text = (content + " " + section).lower()

        if any(kw in text for kw in self.critical_keywords):
            return "critical"

        if any(kw in text for kw in self.high_keywords):
            return "high"

        # Deletions are inherently riskier
        if change_type == "deletion":
            return "medium"

        if any(kw in text for kw in self.low_keywords):
            return "low"

        # Short content = likely cosmetic
        if len(content.strip()) < 80:
            return "low"

        return "medium"

    def _rule_reason(self, content: str, level: str) -> str:
        text = content.lower()
        matched = [kw for kw in self.critical_keywords + self.high_keywords
                   if kw in text]
        if matched:
            return (f"Contains policy-sensitive terms: "
                    f"{', '.join(matched[:4])}")
        return "Rule-based flag — manual review recommended"

    def _rule_recommendation(self, level: str) -> str:
        return {
            "critical": "Immediate legal/compliance team review required",
            "high":     "Review with senior policy team before implementation",
            "medium":   "Standard review process — validate with stakeholders",
            "low":      "Low priority — verify during routine review"
        }.get(level, "Manual review recommended")

    # ------------------------------------------------------------------
    # LLM risk assessment — only for top critical/high
    # ------------------------------------------------------------------
    def _llm_assess(self, change_type: str, change: dict) -> dict:
        content = change.get("new_content") or change.get("content", "")
        section = change.get("section", "Unknown")

        prompt = f"""You are a compliance risk analyst.

Change Type: {change_type.upper()}
Section: {section}
Content: {content[:self.max_content_len]}

Respond ONLY in JSON (no extra text):
{{
    "level": "none|low|medium|high|critical",
    "reason": "one sentence reason",
    "recommendation": "one sentence action"
}}

Risk levels:
- critical: legal/regulatory compliance breach, financial penalties possible
- high: significant obligation or right removed/added, affects many people
- medium: process change, deadline change, threshold change
- low: minor wording, cosmetic, clarification only
- none: no meaningful impact"""

        try:
            response = ollama.chat(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                options={
                    "num_predict": 120,   # short response
                    "temperature": 0      # deterministic
                }
            )
            text = response["message"]["content"]
            import json
            json_match = re.search(r'\{.*?\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"   ⚠️ LLM error: {e}")

        return {
            "level": "medium",
            "reason": "LLM unavailable — rule-based fallback",
            "recommendation": "Manual review recommended"
        }

    def _build_risk(self, change: dict, change_type: str,
                risk: dict) -> dict:
        return {
            "section":        change.get("section", "Unknown"),
            "change_type":    change_type,
            "risk_level":     risk["level"],
            "risk_reason":    risk["reason"],
            "recommendation": risk["recommendation"],
            "llm_analyzed":   "rule-based" not in risk.get(
                                "reason", "").lower(),

            # ── Actual content — shown in report ──────────────────
            "old_content": _truncate(
                change.get("old_content") or change.get("content", "")
                if change_type in ("deletion", "update") else ""
            ),
            "new_content": _truncate(
                change.get("new_content") or change.get("content", "")
                if change_type in ("addition", "update") else ""
            ),
    }