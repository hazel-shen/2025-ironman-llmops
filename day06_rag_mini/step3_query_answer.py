# step3_query_answer.py
import json
import numpy as np
import faiss
from pathlib import Path
from utils_openai import embed, chat_answer

INDEX_DIR = Path("index")

def load_index_and_meta():
    index = faiss.read_index(str(INDEX_DIR / "faiss.index"))
    meta = json.loads((INDEX_DIR / "meta.json").read_text(encoding="utf-8"))
    return index, meta

def retrieve_top_k(index, query_vec, k=1):
    query_mat = np.array([query_vec], dtype="float32")
    D, I = index.search(query_mat, k)
    return D[0], I[0]  # 距離、索引

def main():
    query = "我要怎麼請假？" #TODO:: 請修改這裡

    # 1) 載入索引+文件
    index, meta = load_index_and_meta()
    docs = meta["docs"]

    # 2) 查詢向量
    q_vec = np.array(embed(query), dtype="float32")

    # 3) 檢索
    D, I = retrieve_top_k(index, q_vec, k=1)
    context = docs[I[0]]
    print("🔎 最相關文件：", context)

    # 4) 讓 LLM 生成答案
    system_prompt = "你是一個企業 FAQ 助理。請根據提供的知識庫內容回答使用者問題，若知識庫未涵蓋請說明不知道。"
    user_prompt = f"根據以下知識庫內容回答：\n{context}\n\n問題：{query}"

    # 5) 把兩個 prompt 打印出來
    print("\n===== System Prompt =====")
    print(system_prompt)
    print("\n===== User Prompt =====")
    print(user_prompt)

    answer = chat_answer(system_prompt, user_prompt)
    print("\n🧠 答案：", answer)

if __name__ == "__main__":
    main()
