import os
from typing import List
from dagster import asset
from .chunks import chunks

# 📄 資產：vectors
# 功能：呼叫 OpenAI Embeddings API，將每個 chunk 轉換成向量
@asset(description="每個 chunk 的向量")
def vectors(context, chunks: List[str]) -> List[List[float]]:
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 未設定，無法呼叫 OpenAI Embeddings。")

    model = os.getenv("QUERY_EMBEDDING_MODEL", "text-embedding-3-small")
    client = OpenAI(api_key=api_key)

    resp = client.embeddings.create(model=model, input=chunks)
    vecs = [d.embedding for d in resp.data]

    context.log.info(f"嵌入完成：{len(vecs)} 向量，模型={model}")
    return vecs
