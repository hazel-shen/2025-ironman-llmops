# services/embed_cache_redis.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Callable, Awaitable, Tuple
import json
import numpy as np

from services.redis_client import get_redis

Vector = List[float]
EmbedFn = Callable[[str], Awaitable[Vector]]

def _l2_normalize(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v) + 1e-8
    return v / n

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

class EmbeddingCacheRedis:
    """
    輕量級語意快取（Redis 持久化版本）
    - 每筆資料存成一個 Redis Hash: {prefix}:item:{id}
        fields:
          q: question (str)
          a: answer (str)
          v: vector JSON (list[float], 已 normalize)
          m: meta JSON (dict)
    - 以 Set 索引所有 id: {prefix}:ids
    - 以 INCR 產生遞增 id: {prefix}:next_id
    - 查詢：拿 query 向量 → 掃描所有 id → cosine 相似度 → 命中門檻回傳
      * 線性掃描 O(N)；適合小～中量 demo。大量資料時建議換 Redis Stack 或 FAISS/pgvector。
    """
    def __init__(self, dim: int, embed_fn: EmbedFn, prefix: str = "embed_cache"):
        self.dim = dim
        self._embed = embed_fn
        self.prefix = prefix

        self.key_ids = f"{prefix}:ids"
        self.key_next = f"{prefix}:next_id"  # INCR 產 id
        # item key: f"{prefix}:item:{id}"

    # ---- public API ----
    async def upsert(self, question: str, answer: str, meta: Dict[str, Any]) -> int:
        r = get_redis()

        # 1) 產生向量（normalize 後存）
        vec = await self._to_vec(await self._embed(question))

        # 2) 產生 id（遞增）
        item_id = int(await r.incr(self.key_next))

        # 3) 寫入 Hash
        key = self._item_key(item_id)
        await r.hset(
            key,
            mapping={
                "q": question,
                "a": answer,
                "v": json.dumps(vec.tolist()),
                "m": json.dumps(meta, ensure_ascii=False),
            },
        )

        # 4) 收錄於 ids 索引
        await r.sadd(self.key_ids, item_id)
        return item_id

    async def search_similar(self, query: str, threshold: float = 0.92) -> Optional[Dict[str, Any]]:
        r = get_redis()
        ids = await r.smembers(self.key_ids)
        if not ids:
            return None

        q_vec = await self._to_vec(await self._embed(query))

        # 逐筆計算 cosine，相似度最高且 >= threshold 就回傳
        best: Tuple[float, Optional[Dict[str, Any]]] = (-1.0, None)

        # Pipeline 可加速；這裡直接簡化逐筆取
        for sid in ids:
            key = self._item_key(int(sid))
            data = await r.hgetall(key)
            if not data:
                continue

            try:
                v = np.array(json.loads(data.get("v", "[]")), dtype=np.float32)
            except Exception:
                continue

            sim = _cosine(q_vec, v)
            if sim > best[0]:
                # 準備 payload
                payload = {
                    "question": data.get("q", ""),
                    "answer": data.get("a", ""),
                }
                # 附帶 meta
                try:
                    payload.update(json.loads(data.get("m", "{}")))
                except Exception:
                    pass
                best = (sim, payload)

        if best[0] >= threshold and best[1] is not None:
            return best[1]
        return None

    async def size(self) -> int:
        r = get_redis()
        return int(await r.scard(self.key_ids))

    async def clear(self) -> None:
        """小工具：清空整個語意快取（慎用）"""
        r = get_redis()
        ids = await r.smembers(self.key_ids)
        pipe = r.pipeline(transaction=False)
        for sid in ids:
            pipe.delete(self._item_key(int(sid)))
        pipe.delete(self.key_ids)
        pipe.delete(self.key_next)
        await pipe.execute()

    # ---- helpers ----
    async def _to_vec(self, arr: Vector) -> np.ndarray:
        v = np.array(arr, dtype=np.float32)
        # 維度檢查（保守起見；不符就截/補零）
        if v.shape[0] != self.dim:
            if v.shape[0] > self.dim:
                v = v[: self.dim]
            else:
                pad = np.zeros((self.dim - v.shape[0],), dtype=np.float32)
                v = np.concatenate([v, pad], axis=0)
        return _l2_normalize(v)

    def _item_key(self, item_id: int) -> str:
        return f"{self.prefix}:item:{item_id}"
