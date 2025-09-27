# steps/embed.py
from __future__ import annotations
import os, math, hashlib
from typing import List

def _should_use_openai() -> bool:
    flag = os.getenv("USE_OPENAI", "false").strip().lower()
    return bool(os.getenv("OPENAI_API_KEY")) and flag in {"1","true","yes","y","on"}

def _openai_embed(texts: List[str]) -> List[List[float]]:
    from openai import OpenAI
    client = OpenAI()
    print("🧠 使用 OpenAI Embeddings (text-embedding-3-small)")
    resp = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return [d.embedding for d in resp.data]

_DIM = 384
def _hashing_vector(s: str, dim: int = _DIM) -> List[float]:
    vec = [0.0] * dim
    for token in s.split():
        h = int(hashlib.sha1(token.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 1) & 1 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(x*x for x in vec)) or 1.0
    return [x / norm for x in vec]

def _local_embed(texts: List[str]) -> List[List[float]]:
    print("📊 使用 Local Hashing Embeddings")
    return [_hashing_vector(t) for t in texts]

def embed_texts(texts: List[str]) -> List[List[float]]:
    if _should_use_openai():
        return _openai_embed(texts)
    return _local_embed(texts)
