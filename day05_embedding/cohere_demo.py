import cohere
import numpy as np
import os
from dotenv import load_dotenv

# 載入 .env 檔案，讀取環境變數（例如 API Key）
load_dotenv()

# 從環境變數取得 Cohere API Key
api_key = os.getenv("COHERE_API_KEY")
if not api_key:
    # 若沒有設定金鑰就直接中斷
    raise RuntimeError("❌ 找不到 COHERE_API_KEY，請確認 .env 或環境變數設定")

# 初始化 Cohere Client
co = cohere.Client(api_key)

# 測試用的三個句子
texts = ["我今天請假", "我要休假", "我想去旅行"]

# 呼叫 Cohere 的 Embed API
# - model="embed-english-v3.0"：使用 Cohere 最新的英文向量模型（多語言也有一定支援）
# - input_type：可設定 "search_document"（文件庫向量）或 "search_query"（查詢向量）
resp = co.embed(
    texts=texts,
    model="embed-english-v3.0",
    input_type="search_document"
)

# 取得向量結果，轉成 numpy array
# shape: (3, 1024) → 三個句子，每個句子轉成 1024 維向量
embs = np.array(resp.embeddings)

print(f"Embeddings shape: {embs.shape[0]} x {embs.shape[1]}")

# 定義 cosine similarity 計算函式
def cos(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

# 計算相似度
print("請假 vs 休假 相似度:", round(cos(embs[0], embs[1]), 3))
print("休假 vs 旅行 相似度:", round(cos(embs[1], embs[2]), 3))
print("請假 vs 旅行 相似度:", round(cos(embs[0], embs[2]), 3))
