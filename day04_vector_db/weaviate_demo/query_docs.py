# query_docs.py
# 這個程式展示 Weaviate 的「查詢流程」：
# 1. 連線到本地 Weaviate 伺服器
# 2. 讀取 Docs collection
# 3. 印出目前有幾筆文件
# 4. 準備一個「模擬 query 向量」(這裡用亂數取代)
# 5. 用 near_vector 檢索，找出最相近的文件
# ⚠️ 注意：這裡的 query 向量是隨機產生的，沒有語意，不會真的跟「請假」有關。
# 如果要真的用「請假」去查詢，必須把文字丟到 Embedding 模型（例如 OpenAI）
# 轉成語意向量，再拿去檢索。這樣結果才會和語意一致。

import numpy as np
import weaviate
from weaviate.classes.query import MetadataQuery

# --- 1) 連線到本地 Weaviate ---
HOST, REST_PORT, GRPC_PORT = "localhost", 8080, 50052
client = weaviate.connect_to_local(host=HOST, port=REST_PORT, grpc_port=GRPC_PORT)

try:
    # --- 2) 讀取 Docs collection ---
    col = client.collections.get("Docs")

    # --- 3) 檢查目前有幾筆文件 ---
    agg = col.aggregate.over_all(total_count=True)
    print("📦 total_count:", agg.total_count)

    # --- 4) 準備一個「模擬 query 向量」---
    # ⚠️ 現在只是隨機亂數 → 沒有任何語意
    # 在真實應用中，這裡應該是：
    #   - 使用者輸入文字（例如 "請假流程"）
    #   - 用 Embedding 模型轉成向量 (e.g., OpenAI Embedding API)
    #   - 再拿這個向量去檢索
    qvec = np.random.random(128).astype("float32").tolist()

    # --- 5) 檢索：找出與 query 向量最相近的文件 ---
    res = col.query.near_vector(
        near_vector=qvec,
        target_vector="default",
        limit=1,
        return_metadata=MetadataQuery(distance=True),
    )

    # --- 6) 印出檢索結果 ---
    print("🔍 query result:", [o.properties for o in res.objects])

finally:
    client.close()
