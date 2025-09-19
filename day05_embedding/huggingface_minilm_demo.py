from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

texts = ["我今天請假", "我要休假", "我想去旅行"]
embs = model.encode(texts)

sim = np.dot(embs[0], embs[1]) / (np.linalg.norm(embs[0]) * np.linalg.norm(embs[1]))
print("請假 vs 休假 相似度:", sim)
sim = np.dot(embs[1], embs[2]) / (np.linalg.norm(embs[1]) * np.linalg.norm(embs[2]))
print("休假 vs 旅行 相似度:", sim)
sim = np.dot(embs[0], embs[2]) / (np.linalg.norm(embs[0]) * np.linalg.norm(embs[2]))
print("請假 vs 旅行 相似度:", sim)