from openai import OpenAI
from dotenv import load_dotenv
import numpy as np
import os

load_dotenv()

client = OpenAI()

# 讀取 .env 檔案裡面的環境變數
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("沒有找到 OPEN_API_KEY，請檢察環境變數！")

# 比較這兩個字串的相近程度
texts = ["鐵人賽好熱血", "我想寫一個 QA Bot"]
embeddings = [client.embeddings.create(model="text-embedding-3-small", input=t).data[0].embedding for t in texts]

similarity = np.dot(embeddings[0], embeddings[1]) / (np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1]))
print("Cosine similarity:", similarity)