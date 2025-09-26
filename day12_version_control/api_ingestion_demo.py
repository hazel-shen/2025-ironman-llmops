# api_ingestion_demo.py
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

# 模擬 API 回傳的 JSON
sample_json = """
{
  "faqs": [
    {"q": "上班時間", "a": "上午 9 點至下午 6 點"},
    {"q": "請假規則", "a": "需提前一天提出申請，緊急情況可事後補辦"},
    {"q": "加班補休", "a": "加班工時可折換補休，需於一個月內使用完畢"},
    {"q": "報銷流程", "a": "需提供正式發票，金額超過 1000 元需經理簽核"}
  ]
}
"""

def load_json(data: str):
    obj = json.loads(data)
    # 把每個 QA 合併成一個段落
    return [f"Q: {x['q']} A: {x['a']}" for x in obj["faqs"]]

def build_index(docs):
    vec = TfidfVectorizer(analyzer="char", ngram_range=(1,3))
    X = vec.fit_transform(docs)
    nn = NearestNeighbors(metric="cosine").fit(X)
    return vec, nn, docs

def query(q: str, vec, nn, docs, topk=2):
    qv = vec.transform([q])
    k = min(topk, len(docs))
    dist, idx = nn.kneighbors(qv, n_neighbors=k)
    print(f"\nQ: {q}")
    for d, i in zip(dist[0], idx[0]):
        print(f"- {docs[i]} (score={1-d:.4f})")

if __name__ == "__main__":
    docs = load_json(sample_json)
    print(f"載入完成，共 {len(docs)} 筆 FAQ")

    vec, nn, docs = build_index(docs)
    query("加班", vec, nn, docs)
    query("報銷", vec, nn, docs)
