# embedding_comparison.py
from openai import OpenAI
from dotenv import load_dotenv
import numpy as np
import os

# 載入 .env 檔案
load_dotenv()

# 讀取 OPENAI_API_KEY
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("沒有找到 OPENAI_API_KEY，請檢查境變數！")

# 初始化 OpenAI client
client = OpenAI()

def embedding(text: str):
    """取得文字的向量表示"""
    return client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    ).data[0].embedding

def cosine_similarity(v1, v2):
    """計算兩個向量的餘弦相似度"""
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

# 舊版 FAQ vs 新版 FAQ
old_text = "退貨政策：商品需在 7 天內退回，且保持完整包裝。"
new_text = "退貨政策：商品需在 14 天內退回，並保持原始包裝未損壞。"

vec_old = embedding(old_text)
vec_new = embedding(new_text)

similarity = cosine_similarity(vec_old, vec_new)
print(f"語意相似度: {similarity:.4f}")

# 設定門檻（可依需求調整，例如 0.95）
if similarity < 0.95:
    print("⚠️ 偵測到重要差異，需要更新知識庫！")
else:
    print("✅ 差異不大，可以不用更新。")
