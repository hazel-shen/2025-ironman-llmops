import json
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

_USE_FAKE = os.getenv("USE_FAKE_EMBEDDINGS", "false").lower() in {"1","true","yes"}

def _fake_embed(texts: List[str]) -> List[List[float]]:
    """
    若沒有 API Key 或想省成本，可用隨機/可重現向量做示意。
    這裡用簡單 hash -> 低維浮點，避免引入 heavy 套件。
    """
    import math
    vecs: List[List[float]] = []
    for t in texts:
        h = abs(hash(t))
        # 產生簡單的 8 維向量
        v = [( ((h >> (i*8)) & 0xFF) / 255.0 ) for i in range(8)]
        # L2 normalize
        norm = math.sqrt(sum(x*x for x in v)) or 1.0
        vecs.append([x / norm for x in v])
    return vecs

def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    真實向量：使用 OpenAI embeddings
    假向量：_fake_embed（將 USE_FAKE_EMBEDDINGS 設為 true）
    """
    if _USE_FAKE:
        return _fake_embed(texts)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # 自動 fallback，避免程式中斷
        return _fake_embed(texts)

    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    resp = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    return [d.embedding for d in resp.data]

def save_vector_index(chunks: List[str], vectors: List[List[float]], out_path: str, meta: Optional[Dict[str, Any]] = None):
    """
    以 JSON 模擬「上傳向量 DB」。日後可替換為 Weaviate / Pinecone / FAISS。
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    payload: Dict[str, Any] = {
        "meta": meta or {},
        "items": [{"id": i, "chunk": c, "vector": v} for i, (c, v) in enumerate(zip(chunks, vectors))]
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
