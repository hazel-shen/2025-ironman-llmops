# pinecone_demo.py
from pinecone import Pinecone, ServerlessSpec
import os
import numpy as np
from dotenv import load_dotenv

# 載入 .env
load_dotenv()

# 讀取金鑰
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
if not PINECONE_API_KEY:
    raise RuntimeError("❌ 找不到 PINECONE_API_KEY，請確認 .env 或環境變數設定")

# 初始化
pc = Pinecone(api_key=PINECONE_API_KEY)
index_name = "demo-index"

# 建立 index（如果不存在）
if index_name not in [idx["name"] for idx in pc.list_indexes()]:
    pc.create_index(
        name=index_name,
        dimension=128,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )

index = pc.Index(index_name)

# 定義文件，可以在這邊修改測試資料
docs = [
    {"id": "101", "text": "員工請假需要提前三天申請"},
    {"id": "102", "text": "差旅報銷需附上發票與行程單"},
    {"id": "103", "text": "出差前需要完成出差申請表"},
]

# 先檢查目前 index 狀態
stats = index.describe_index_stats()
existing_count = stats["total_vector_count"]

if existing_count == 0:
    print("🆕 第一次執行：插入文件")
else:
    print("♻️  文件已存在：這次會更新向量內容")

# 插入 / 更新文件
vectors = []
for doc in docs:
    vec = np.random.random(128).astype("float32").tolist()
    vectors.append((doc["id"], vec, {"text": doc["text"]}))

index.upsert(vectors=vectors)

# 再檢查狀態
new_stats = index.describe_index_stats()
print(f"✅ 向量總數: {new_stats['total_vector_count']}")

# 模擬查詢
query_vec = np.random.random(128).astype("float32").tolist()
res = index.query(vector=query_vec, top_k=2, include_metadata=True)

print("\n🔍 查詢結果：")
for match in res["matches"]:
    print(f"- {match['metadata']['text']} (score={match['score']:.4f})")
