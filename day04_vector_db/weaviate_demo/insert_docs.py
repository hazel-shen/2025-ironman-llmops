# insert_docs.py
import numpy as np
import weaviate
from weaviate.classes.config import Property, DataType, Configure

HOST, REST_PORT, GRPC_PORT = "localhost", 8080, 50052
client = weaviate.connect_to_local(host=HOST, port=REST_PORT, grpc_port=GRPC_PORT)

try:
    print("ready?", client.is_ready())

    # 如果已經有 Docs 集合，刪掉重建
    if "Docs" in client.collections.list_all():
        client.collections.delete("Docs")

    # 建立一個 Docs collection
    client.collections.create(
        name="Docs",
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vector_config=Configure.Vectors.self_provided(name="default"),
    )
    col = client.collections.get("Docs")

    # 插入兩筆資料
    dim = 128
    docs = [
        "RAG 是 Retrieval-Augmented Generation",
        "請假流程需要先主管簽核，再送人資系統",
    ]

    for text in docs:
        vec = np.random.random(dim).astype("float32").tolist()
        obj_uuid = col.data.insert({"text": text}, vector={"default": vec})
        print(f"✅ inserted: {text}, uuid={obj_uuid}")

finally:
    client.close()
