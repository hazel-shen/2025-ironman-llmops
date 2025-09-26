# web_ingestion_demo.py
import requests
from bs4 import BeautifulSoup
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

def clean_text(s: str) -> str:
    """移除多餘空白"""
    return re.sub(r"\s+", " ", s).strip()

def load_web(url: str):
    """抓取網頁並擷取所有 <p> 文字"""
    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")
    paras = [clean_text(p.get_text()) for p in soup.find_all("p")]
    return [p for p in paras if p]

def build_index(docs):
    """建立向量索引 (支援中文)"""
    vec = TfidfVectorizer(analyzer="char", ngram_range=(1,3))
    X = vec.fit_transform(docs)
    nn = NearestNeighbors(metric="cosine").fit(X)
    return vec, nn, docs

def query(q: str, vec, nn, docs, topk: int = 3):
    """查詢，並回傳最相似的段落"""
    qv = vec.transform([q])
    k = min(topk, len(docs))
    dist, idx = nn.kneighbors(qv, n_neighbors=k)
    print(f"\nQ: {q}")
    for d, i in zip(dist[0], idx[0]):
        print(f"- {docs[i]} (score={1-d:.4f})")

if __name__ == "__main__":
    # 換成任一新聞網址，例如 iThome 新聞
    url = "https://www.ithome.com.tw/article/162165"
    docs = load_web(url)
    print(f"載入完成，共 {len(docs)} 段落")

    vec, nn, docs = build_index(docs)

    # 範例查詢
    query("生成式AI", vec, nn, docs)
    query("微軟", vec, nn, docs)
