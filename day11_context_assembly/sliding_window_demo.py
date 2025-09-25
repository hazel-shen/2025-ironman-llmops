# sliding_window_demo.py
# 功能：從 reranked.json 讀取 Day10 的重排序結果，對每篇文件擷取「滑動視窗片段」，
#      再以中文 Prompt 模板組裝上下文。
# 使用方式：
#   python sliding_window_demo.py --in reranked.json --top-n 3 --window-size 120

import os
import sys
import json
import argparse

DEFAULT_IN_PATH = "reranked.json"

def load_reranked(path: str, top_n: int = 3):
    """
    讀取 reranked.json，回傳：
      - query: 查詢字串
      - docs:  前 top_n 筆（依 Reranker 分數排序）的文件文字列表
      - items: 完整的前 top_n 物件（含分數），方便列印對照
    """
    if not os.path.exists(path):
        print(f"找不到輸入檔：{path}。請先執行 Day10 的腳本產生 reranked.json")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "reranked" not in data or not data["reranked"]:
        print("reranked.json 裡沒有 'reranked' 欄位或內容為空。請確認 Day10 已經完成重排序輸出。")
        sys.exit(1)

    items = data["reranked"][:top_n]  # 已是由高到低的重排結果
    docs = [it["text"] for it in items]
    query = data.get("query", "")

    return query, docs, items

def extract_snippet(doc: str, query: str, window_size: int = 120) -> str:
    """
    以最直覺的方式在文件中尋找 query 的位置：
      - 直接用大小寫不敏感的字串搜尋
      - 找不到時，退回取文件開頭的前 window_size 個字元
    實務上可改用關鍵句比對或嵌入對齊來尋找更準確的片段。
    """
    # 基本大小寫不敏感搜尋（對中文通常等同原樣）
    idx = doc.lower().find(query.lower()) if query else -1
    if idx == -1:
        return doc[:window_size]

    start = max(0, idx - window_size // 2)
    end = min(len(doc), idx + window_size // 2)
    return doc[start:end]

def build_prompt_window(query: str, docs: list, max_docs: int = 3, window_size: int = 120) -> str:
    """
    針對前 max_docs 篇文件擷取片段並用分隔線組裝為中文 Prompt。
    """
    snippets = [extract_snippet(doc, query, window_size) for doc in docs[:max_docs]]
    context = "\n---（片段分隔）---\n".join(snippets)

    prompt = f"""
你是一個樂於助人的助手。
請僅根據下面提供的「上下文片段」回答問題。
若在片段中找不到答案，請回答「我不知道」。

問題：{query}

上下文片段：
{context}

請用完整句子作答：
"""
    return prompt.strip()

def main():
    parser = argparse.ArgumentParser(description="從 reranked.json 讀取重排結果，做 Sliding Window 上下文組裝。")
    parser.add_argument("--in", dest="in_path", default=DEFAULT_IN_PATH, help="輸入檔（預設：reranked.json）")
    parser.add_argument("--top-n", dest="top_n", type=int, default=3, help="取前 N 筆重排結果（預設：3）")
    parser.add_argument("--window-size", dest="window_size", type=int, default=120, help="每段片段的視窗大小（字元數，預設：120）")
    args = parser.parse_args()

    # 讀取前 N 筆重排結果
    query, docs, items = load_reranked(args.in_path, top_n=args.top_n)

    # 顯示原始將用到的文件與分數
    print("=== 將使用的前 N 筆（重排序後）===")
    for i, it in enumerate(items, 1):
        re = it.get("reranker_score", None)
        ret = it.get("retriever_score", None)
        idx = it.get("idx", None)
        print(f"[{i:02d}] re={re:.4f} | ret={ret:.4f} | idx={idx} | {it['text']}")

    # 顯示擷取後的片段（方便文章對照）
    print("\n=== 擷取出的片段（Sliding Window）===")
    for i, doc in enumerate(docs[:args.top_n], 1):
        snippet = extract_snippet(doc, query, args.window_size)
        print(f"[{i:02d}] 片段：{snippet}")

    # 建立中文 Prompt（Sliding Window）
    prompt = build_prompt_window(query, docs, max_docs=args.top_n, window_size=args.window_size)

    print("\n=== （Sliding Window）組裝後的提示詞 ===\n")
    print(prompt)

if __name__ == "__main__":
    main()
