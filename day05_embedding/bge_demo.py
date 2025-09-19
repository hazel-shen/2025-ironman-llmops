from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer('BAAI/bge-small-zh-v1.5')

texts = ["我今天請假", "我要休假", "我想去旅行"]
embs = model.encode(texts, normalize_embeddings=True)

sim = np.dot(embs[0], embs[1])
print("請假 vs 休假 相似度:", sim)
sim = np.dot(embs[1], embs[2])
print("休假 vs 旅行 相似度:", sim)
sim = np.dot(embs[0], embs[2])
print("請假 vs 旅行 相似度:", sim)