# app/llm_small.py
import os

SMALL_MODEL_PRICE_PER_1K = float(os.getenv("SMALL_MODEL_PRICE_PER_1K", "0"))

def _get(obj, name, default=None):
    # 同時支援 Pydantic 物件與 dict
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)

def _estimate_tokens(text: str) -> int:
    ascii_words = len([w for w in text.split() if any(c.isascii() for c in w)])
    cjk_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    return ascii_words + cjk_chars

def answer_with_small_model(query: str, contexts):
    # 「完全沒命中」= contexts 為空 或 全部 score<=0
    no_hit = (not contexts) or all((_get(c, "score", 0) or 0) <= 0 for c in contexts)

    if no_hit:
        ans = "目前知識庫沒有足夠線索，建議改以工單/人力支援處理。"
    else:
        # 取分數最高的片段做模板拼接
        top = max(contexts, key=lambda c: (_get(c, "score", 0) or 0))
        ctx_text = _get(top, "text", "")
        ans = f"根據知識庫：{ctx_text}"

    used_tokens = _estimate_tokens(query) + _estimate_tokens(ans)
    cost = (used_tokens / 1000.0) * SMALL_MODEL_PRICE_PER_1K
    return ans, used_tokens, cost
