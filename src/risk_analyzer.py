import ollama

class RiskAnalyzer:
    def __init__(self, llm_model="gemma3:4b"):
        self.llm_model = llm_model

    def analyze(self, diff_results: dict) -> list:
        risks = []

        all_changes = (
            [("addition", c) for c in diff_results["additions"]] +
            [("deletion", c) for c in diff_results["deletions"]] +
            [("update",   c) for c in diff_results["updates"]]
        )

        for change_type, change in all_changes:
            content = change.get("new_content") or change.get("content", "")
            if not content:
                continue

            risk = self._assess_risk(change_type, content, change["section"])
            if risk["level"] != "none":
                risks.append({
                    "section": change["section"],
                    "change_type": change_type,
                    "risk_level": risk["level"],     # low / medium / high / critical
                    "risk_reason": risk["reason"],
                    "recommendation": risk["recommendation"]
                })

        return sorted(risks, key=lambda x: 
            ["none","low","medium","high","critical"].index(x["risk_level"]), 
            reverse=True
        )

    def _assess_risk(self, change_type: str, content: str, section: str) -> dict:
        prompt = f"""
        You are a compliance and risk analyst reviewing policy document changes.
        
        Change Type: {change_type.upper()}
        Section: {section}
        Content: {content}

        Assess the risk of this change. Respond ONLY in JSON:
        {{
            "level": "none|low|medium|high|critical",
            "reason": "brief reason in one sentence",
            "recommendation": "what action to take"
        }}

        Risk criteria:
        - critical: legal/regulatory compliance breach, financial penalties possible
        - high: significant obligation or right removed/added, affects many people
        - medium: process change, deadline change, threshold change
        - low: minor wording, cosmetic, clarification only
        - none: no meaningful impact
        """
        response = ollama.chat(
            model=self.llm_model,
            messages=[{"role": "user", "content": prompt}]
        )

        import json, re
        text = response["message"]["content"]
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"level": "low", "reason": "Could not assess", "recommendation": "Manual review recommended"}