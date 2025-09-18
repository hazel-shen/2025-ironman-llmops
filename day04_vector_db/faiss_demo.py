import faiss
import numpy as np

# 模擬兩個向量 (128 維)
d = 128
xb = np.random.random((5, d)).astype('float32')
xq = np.random.random((1, d)).astype('float32')

index = faiss.IndexFlatL2(d)  # L2 距離
index.add(xb)                 # 建立索引
D, I = index.search(xq, k=2)  # 查詢
print("相似度距離:", D)
print("相似向量索引:", I)