import re
from typing import Dict, List, Tuple

def compile_patterns(patterns: List[str]) -> List[re.Pattern]:
    return [re.compile(p) for p in patterns]

def sanitize_input(text: str) -> str:
    if not text:
        return ""
    # 移除控制字元（null、escape、unicode 控制符號）
    text = re.sub(r"[\x00-\x1f\x7f]", "", text)
    # 移除 HTML/Script 標籤
    text = re.sub(r"<.*?>", "", text)
    return text

class Guardrails:
    def __init__(self, policy: Dict):
        self.policy = policy
        self.input_patterns = compile_patterns(policy.get("input", {}).get("deny_patterns", []))
        self.output_patterns = compile_patterns(policy.get("output", {}).get("deny_patterns", []))

    def check_input(self, text: str, mode: str) -> Tuple[bool, List[str]]:
        violations = []
        if mode == "off":
            return False, violations
        for pat in self.input_patterns:
            if pat.search(text or ""):
                violations.append(f"input:{pat.pattern}")
                if mode == "enforce":
                    return True, violations
        return False, violations

    def redact_pii(self, text: str, mode: str) -> Tuple[str, Dict[str, int]]:
        stats = {}
        result = text or ""
        if mode == "off":
            return result, stats

        MAX_TEXT_LENGTH = 50000  # 設定合理上限
        if len(result) > MAX_TEXT_LENGTH:
            result = result[:MAX_TEXT_LENGTH]
            stats["truncated"] = True

        pii_cfg = self.policy.get("pii", {}).get("redact", [])

        if "email" in pii_cfg:
            result, n = re.subn(
                r"[A-Za-z0-9._=\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
                "[REDACTED_EMAIL]",
                result
            )
            stats["email"] = n

        if "phone" in pii_cfg:
            result, n1 = re.subn(
                r"(09\d{2}-\d{3}-\d{3}|09\d{8})",
                "[REDACTED_PHONE]",
                result
            )
            result, n2 = re.subn(
                r"(\+?\d[\d\-\s]{7,}\d)",
                "[REDACTED_PHONE]",
                result
            )
            stats["phone"] = n1 + n2

        # 金鑰遮罩
        result, n3 = re.subn(r"sk-[a-zA-Z0-9]{20,}", "[REDACTED_APIKEY]", result)
        if n3 > 0:
            stats["apikey"] = n3

        return result, stats

    def check_output(self, text: str, mode: str) -> Tuple[bool, List[str]]:
        violations = []
        if mode == "off":
            return False, violations
        for pat in self.output_patterns:
            if pat.search(text or ""):
                violations.append(f"output:{pat.pattern}")
                if mode == "enforce":
                    return True, violations
        return False, violations

    def enforce_acl(self, user_role: str, doc_ids: List[str], mode: str) -> Tuple[bool, List[str]]:
        violations = []
        if mode == "off":
            return True, violations

        docs = self.policy.get("retrieval", {}).get("docs", {})
        for doc_id in doc_ids:
            roles = docs.get(doc_id, {}).get("roles", [])
            if user_role not in roles:
                violations.append(f"acl_denied:{doc_id}")
                if mode == "enforce":
                    return False, violations
        return True, violations
