import pytest
from services.cache import PromptCache

@pytest.mark.asyncio
async def test_prompt_cache_basic():
    pc = PromptCache()
    q = "什麼是快取？"
    payload = {"answer": "A", "source": "llm", "prompt_tokens": 1, "completion_tokens": 2, "cost_usd": 0.0}
    await pc.set(q, payload, ttl=60)
    got = await pc.get(q)
    assert got is not None
    assert got["answer"] == "A"
    assert got["source"] == "llm"
