import pytest
from services.embed_cache_redis import EmbeddingCacheRedis

@pytest.mark.asyncio
async def test_embed_cache_redis_upsert_and_search(lower_threshold, mock_llm):
    # 注意：mock_llm 會讓 embed 向量固定，任何相似查詢都會命中
    from services.llm import LLMService
    ec = EmbeddingCacheRedis(dim=1536, embed_fn=LLMService().embed)

    item_id = await ec.upsert("什麼是快取？", "快取是加速讀取的技術。", {"prompt_tokens": 5, "completion_tokens": 7, "cost_usd": 0.0})
    assert isinstance(item_id, int)

    near = await ec.search_similar("請解釋快取是什麼")
    assert near is not None
    assert "answer" in near
    assert near["answer"].startswith("快取")
