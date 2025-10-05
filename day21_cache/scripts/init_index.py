import asyncio
from day21_cache.services.embed_cache_redis import EmbeddingCache

async def main():
    ec = EmbeddingCache(dim=384)
    samples = [
        ("什麼是快取？", "快取是一種把常用資料暫存起來以加速讀取的技術。"),
        ("為什麼要用向量相似度？", "用來找到語意上相近的問題與答案，提升命中率。"),
    ]
    for q, a in samples:
        await ec.upsert(q, a, {"prompt_tokens": 5, "completion_tokens": 15, "cost_usd": 0.0})
    print("Initialized in-memory embedding cache with samples (lifetime only).")

if __name__ == "__main__":
    asyncio.run(main())
