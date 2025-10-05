from typing import Optional, List
from dataclasses import dataclass
from openai import AsyncOpenAI
from core.config import settings

@dataclass
class LLMResult:
    answer: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: Optional[float] = None

class LLMService:
    def __init__(self) -> None:
        kwargs = {}
        if settings.OPENAI_BASE_URL:
            kwargs["base_url"] = settings.OPENAI_BASE_URL

        # 若未設定 API Key，仍可跑 mock（見 chat() 的 fallback）
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, **kwargs)

    async def chat(self, question: str) -> LLMResult:
        # 若沒設定 OPENAI_API_KEY，回 mock 讓系統仍可運作
        if not settings.OPENAI_API_KEY:
            answer = f"(mock) You asked: {question}\nSet OPENAI_API_KEY to call real API."
            prompt_tokens = max(1, len(question) // 4)
            completion_tokens = max(5, len(answer) // 4)
            return LLMResult(
                answer=answer,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=0.0,
            )

        resp = await self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": question}],
            timeout=settings.OPENAI_TIMEOUT_SECONDS,
        )

        answer = (resp.choices[0].message.content or "").strip()
        usage = resp.usage or None
        prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

        cost = self._estimate_chat_cost(prompt_tokens, completion_tokens)
        return LLMResult(
            answer=answer,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
        )

    async def embed(self, text: str) -> List[float]:
        # 若沒 key，一樣返回 mock embedding（維度需與 EMBED_CACHE_DIM 一致）
        if not settings.OPENAI_API_KEY:
            # 與過去假 embedding 行為不同步，這裡回零向量避免語意誤判
            dim = settings.EMBED_CACHE_DIM
            return [0.0] * dim

        resp = await self.client.embeddings.create(
            model=settings.OPENAI_EMBED_MODEL,
            input=text,
            timeout=settings.OPENAI_TIMEOUT_SECONDS,
        )
        vec = resp.data[0].embedding
        return vec  # type: ignore[return-value]

    @staticmethod
    def _estimate_chat_cost(prompt_tokens: int, completion_tokens: int) -> float:
        # 估算成本（USD）；以 .env/設定檔為準
        p_cost = (prompt_tokens / 1000.0) * settings.PROMPT_COST_PER_1K
        c_cost = (completion_tokens / 1000.0) * settings.COMPLETION_COST_PER_1K
        return round(p_cost + c_cost, 6)
