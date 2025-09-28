"""
最小檢索腳本（OpenAI Embeddings 版本）
-----------------------------------
1) 載入 data/vector_index.json
2) 使用 OpenAI Embeddings 產生 query 向量
3) 以 cosine similarity 找出 Top-K（預設 3 筆）

用法：
    python scripts/query_with_openai.py "加班規則"

需要環境變數：
    OPENAI_API_KEY           OpenAI API 金鑰（必填）
    QUERY_EMBEDDING_MODEL    (可選) 指定查詢 Embedding 模型
                              預設：text-embedding-3-small
"""
import json
import math
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# ────────────────────────────────────────────────────────────
# 環境 & Client
# ────────────────────────────────────────────────────────────
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("沒有找到 OPENAI_API_KEY，請在 .env 或環境變數中設定！")

# 使用環境變數初始化 OpenAI client
client = OpenAI()

# 索引路徑
INDEX = Path(__file__).resolve().parents[1] / "data" / "vector_index.json"

# 預設模型（可被 QUERY_EMBEDDING_MODEL 覆蓋）
DEFAULT_MODEL = "text-embedding-3-small"


# ────────────────────────────────────────────────────────────
# 工具函式
# ────────────────────────────────────────────────────────────
def l2_norm(v):
    return math.sqrt(sum(x * x for x in v)) or 1.0


def cosine(a, b):
    an, bn = l2_norm(a), l2_norm(b)
    return sum(x * y for x, y in zip(a, b)) / (an * bn)


def real_embed_openai(text: str, model_name: str):
    """呼叫 OpenAI 產生單筆查詢向量。"""
    resp = client.embeddings.create(model=model_name, input=[text])
    return resp.data[0].embedding


def choose_model(meta: dict) -> str:
    """
    選擇查詢要用的模型：
    1) 先看環境變數 QUERY_EMBEDDING_MODEL
    2) 再看索引 meta["model"]
    3) 最後回退 DEFAULT_MODEL

    會自動把 'FAKE' 或 'A or B' 這種格式清理為合法單一模型名。
    """
    raw_name = os.getenv("QUERY_EMBEDDING_MODEL") or meta.get("model") or DEFAULT_MODEL
    name = str(raw_name).strip()

    # 若包含 'FAKE' 字樣，直接回退預設真實模型
    if "FAKE" in name.upper():
        return DEFAULT_MODEL

    # 若包含多選或分隔字樣，取第一個候選
    for sep in [" or ", ",", "/"]:
        if sep in name:
            name = name.split(sep)[0].strip()
            break

    # 若清理後仍是空值，回退預設
    return name or DEFAULT_MODEL


# ────────────────────────────────────────────────────────────
# 入口點
# ────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    query = sys.argv[1]

    if not INDEX.exists():
        print(f"Index not found: {INDEX}\n請先執行 Prefect flow 產生索引：\n  python -m flows.daily_pipeline")
        sys.exit(1)

    data = json.loads(INDEX.read_text(encoding="utf-8"))
    items = data.get("items", [])
    meta = data.get("meta", {}) or {}

    if not items:
        print("Index empty. 請先確認 daily_pipeline 是否已成功產生索引內容。")
        sys.exit(1)

    # 選擇查詢用模型（自動清理 meta.model 的不合法值）
    model_name = choose_model(meta)

    # 產生查詢向量（若模型 ID 無效會在此拋出 400 錯誤）
    q_vec = real_embed_openai(query, model_name)

    # 相似度排名
    scored = []
    for it in items:
        v = it["vector"]
        score = cosine(q_vec, v)
        scored.append((score, it["chunk"], it["id"]))

    scored.sort(key=lambda x: x[0], reverse=True)
    topk = scored[:3]

    print(f"\n🔎 Query: {query}")
    print(f"🔧 Query embedding using: {model_name}\n")
    for rank, (score, chunk, cid) in enumerate(topk, start=1):
        print(f"[{rank}] score={score:.4f} | id={cid}\n{chunk}\n")


if __name__ == "__main__":
    main()
