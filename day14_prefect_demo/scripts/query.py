"""
最小檢索腳本：載入 vector_index.json，對輸入 query 做 cosine similarity，
印出 Top-K 最相近的 chunk（預設 3 筆）。
用法：
    python scripts/query.py "加班規則"
"""
import json
import math
import sys
from pathlib import Path

INDEX = Path(__file__).resolve().parents[1] / "data" / "vector_index.json"

def l2_norm(v):
    return math.sqrt(sum(x*x for x in v)) or 1.0

def cosine(a, b):
    # 假設皆已 L2 normalize；若無，這裡保險再除一次
    an, bn = l2_norm(a), l2_norm(b)
    return sum(x*y for x, y in zip(a, b)) / (an * bn)

def fake_embed(text: str):
    # 與 utils.embeddings 的假向量一致原理：簡單 hash -> 8 維
    h = abs(hash(text))
    v = [((h >> (i*8)) & 0xFF) / 255.0 for i in range(8)]
    n = l2_norm(v)
    return [x / n for x in v]

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    query = sys.argv[1]
    if not INDEX.exists():
        print(f"Index not found: {INDEX}. 請先執行 daily_pipeline 產生索引。")
        sys.exit(1)

    data = json.loads(INDEX.read_text(encoding="utf-8"))
    items = data.get("items", [])
    if not items:
        print("Index empty.")
        sys.exit(1)

    # 這裡用假向量查詢（若你用真實 OpenAI 向量，請改為相同模型生成）
    q_vec = fake_embed(query)

    scored = []
    for it in items:
        v = it["vector"]
        score = cosine(q_vec, v)
        scored.append((score, it["chunk"], it["id"]))

    scored.sort(key=lambda x: x[0], reverse=True)
    topk = scored[:3]

    print(f"\n🔎 Query: {query}\n")
    for rank, (score, chunk, cid) in enumerate(topk, start=1):
        print(f"[{rank}] score={score:.4f} | id={cid}\n{chunk}\n")

if __name__ == "__main__":
    main()
