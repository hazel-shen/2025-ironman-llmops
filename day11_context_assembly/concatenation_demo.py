# concatenation_demo.py
# 功能：從 reranked.json 讀取 Day10 的重排序結果，取前 N 筆文件直接拼接為「上下文」，
#      組成中文 Prompt，印出供你複製到 LLM 使用。
# 使用方式：
#   python concatenation_demo.py --in reranked.json --top-n 3

import os
import sys
import json
import argparse

DEFAULT_IN_PATH = "reranked.json"

def load_reranked(path: str, top_n: int = 3):
    """
    讀取 Day10 產生的 reranked.json，回傳：
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

    items = data["reranked"][:top_n]  # 已經是由高到低的重排結果
    docs = [it["text"] for it in items]
    query = data.get("query", "")

    return query, docs, items

def build_prompt_concat(query: str, docs: list, max_docs: int = 3) -> str:
    """
    直接將前 max_docs 篇文件拼接成「上下文」
    （提示詞模板與文字全部為繁體中文）
    """
    selected_docs = docs[:max_docs]
    context = "\n".join(selected_docs)

    prompt = f"""
你是一個樂於助人的助手。
請僅根據下面提供的「上下文」回答問題。
若在上下文中找不到答案，請回答「我不知道」。

問題：{query}

上下文：
{context}

請用完整句子作答：
"""
    return prompt.strip()

def main():
    parser = argparse.ArgumentParser(description="從 reranked.json 讀取重排結果，做 Concatenation 上下文組裝。")
    parser.add_argument("--in", dest="in_path", default=DEFAULT_IN_PATH, help="輸入檔（預設：reranked.json）")
    parser.add_argument("--top-n", dest="top_n", type=int, default=3, help="取前 N 筆重排結果組裝上下文（預設：3）")
    args = parser.parse_args()

    # 讀取前 N 筆重排結果
    query, docs, items = load_reranked(args.in_path, top_n=args.top_n)

    # 顯示將要使用的文件（含分數，便於文章示範對照）
    print("=== 將使用的前 N 筆（重排序後）===")
    for i, it in enumerate(items, 1):
        re = it.get("reranker_score", None)
        ret = it.get("retriever_score", None)
        idx = it.get("idx", None)
        print(f"[{i:02d}] re={re:.4f} | ret={ret:.4f} | idx={idx} | {it['text']}")

    # 建立中文 Prompt（Concatenation）
    prompt = build_prompt_concat(query, docs, max_docs=args.top_n)

    print("\n=== （Concatenation）組裝後的 Prompt ===\n")
    print(prompt)

if __name__ == "__main__":
    main()
