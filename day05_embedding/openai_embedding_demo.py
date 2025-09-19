from openai import OpenAI
from dotenv import load_dotenv
import numpy as np
import os


# 載入 .env
load_dotenv()

# 讀取金鑰
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("❌ 找不到 OPENAI_API_KEY，請確認 .env 或環境變數設定")
client = OpenAI()

texts = ["我今天請假", "我要休假", "我想去旅行"]
embs = [client.embeddings.create(model="text-embedding-3-small", input=t).data[0].embedding for t in texts]

sim = np.dot(embs[0], embs[1]) / (np.linalg.norm(embs[0]) * np.linalg.norm(embs[1]))
print("請假 vs 休假 相似度:", sim)
sim = np.dot(embs[1], embs[2]) / (np.linalg.norm(embs[1]) * np.linalg.norm(embs[2]))
print("休假 vs 旅行 相似度:", sim)
sim = np.dot(embs[0], embs[2]) / (np.linalg.norm(embs[0]) * np.linalg.norm(embs[2]))
print("請假 vs 旅行 相似度:", sim)
