# chunk_ranking_demo.py
# 功能：
#   1) 讀取 reranked.json（Day10 的重排序結果）
#   2) 將前 N 篇文件切成小片段（chunk_size / overlap）
#   3) 使用 Cross-Encoder 對 (query, chunk) 評分並排序
#   4) 取前 M 個片段做「依分數挑片段後再拼接」的上下文組裝
#
# 使用方式：
#   python chunk_ranking_demo.py --in reranked.json --top-n 3 --chunk-size 180 --overlap 40 --top-chunks 3
# 參數說明：
#   --in           輸入 reranked.json
#   --top-n        取前 N 篇文件來切片段（預設 3）
#   --chunk-size   每個片段的目標字元數（預設 180）
#   --overlap      片段之間重疊字元數（預設 40）
#   --top-chunks   最終要拼接進上下文的片段數（預設 3）
#   --model        Cross-Encoder 模型名稱（預設 cross-encoder/ms-marco-MiniLM-L-6-v2）
#   --batch-size   推論批次大小（預設 8）
#   --max-length   Token 最大長度（預設 256）

import os
import sys
import json
import argparse
from typing import List, Tuple, Dict

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification


DEFAULT_IN_PATH = "reranked.json"
DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def load_reranked(path: str, top_n: int = 3) -> Tuple[str, List[str], List[Dict]]:
    """
    讀取 reranked.json，回傳：
      - query: 查詢字串
      - docs:  前 top_n 篇文件（依 Reranker 分數排序）
      - items: 前 top_n 個物件（含分數與原索引），方便列印對照
    """
    if not os.path.exists(path):
        print(f"找不到輸入檔：{path}。請先完成 Day10 產生 reranked.json")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "reranked" not in data or not data["reranked"]:
        print("reranked.json 缺少 'reranked' 欄位或內容為空。請確認 Day10 的重排序輸出。")
        sys.exit(1)

    items = data["reranked"][:top_n]  # 已由高到低排序
    docs = [it["text"] for it in items]
    query = data.get("query", "")
    return query, docs, items


def chunk_text(text: str, chunk_size: int = 180, overlap: int = 40) -> List[str]:
    """
    將長文字切成多個片段：
      - 每段約 chunk_size 字元
      - 相鄰片段重疊 overlap 字元（避免切斷關鍵語境）
    備註：此為簡單的「字元長度」切分；實務可換成句子分割或 tokenizer 依 token 數切分。
    """
    if chunk_size <= 0:
        return [text]
    if overlap >= chunk_size:
        overlap = max(0, chunk_size // 4)  # 避免重疊大於等於片段長度

    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + chunk_size)
        chunks.append(text[start:end])
        if end == n:
            break
        start = end - overlap  # 往前回退 overlap，再繼續切
    return chunks


def build_chunks(docs: List[str], chunk_size: int, overlap: int) -> List[Dict]:
    """
    為每篇文件建立片段，並附上來源資訊以便對照：
      回傳每個片段的 dict：
      {
        "doc_id": int,       # 來自第幾篇文件（從 0 起算）
        "chunk_id": int,     # 此文件的第幾個片段（從 0 起算）
        "text": str,
      }
    """
    all_chunks = []
    for di, doc in enumerate(docs):
        parts = chunk_text(doc, chunk_size=chunk_size, overlap=overlap)
        for ci, part in enumerate(parts):
            all_chunks.append({"doc_id": di, "chunk_id": ci, "text": part})
    return all_chunks


def pick_device() -> torch.device:
    """自動選擇運算裝置：CUDA > MPS(Apple) > CPU"""
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def score_chunks_with_ce(
    query: str,
    chunks: List[Dict],
    model_name: str,
    device: torch.device,
    batch_size: int = 8,
    max_len: int = 256,
) -> List[Dict]:
    """
    使用 Cross-Encoder 對每個 (query, chunk['text']) 打分。
    回傳附加 "score" 欄位的 chunks 清單。
    """
    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.to(device)
    model.eval()

    texts = [c["text"] for c in chunks]
    scores: List[float] = []
    with torch.no_grad():
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            inputs = tok(
                [query] * len(batch),
                batch,
                padding=True,
                truncation=True,
                max_length=max_len,
                return_tensors="pt",
            )
            inputs = {k: v.to(device) for k, v in inputs.items()}
            logits = model(**inputs).logits.squeeze(-1)  # (batch,)
            scores.extend(logits.detach().to("cpu").tolist())

    # 把分數貼回各 chunk
    out = []
    for c, s in zip(chunks, scores):
        item = dict(c)
        item["score"] = float(s)
        out.append(item)
    return out


def build_prompt_from_top_chunks(query: str, top_chunks: List[Dict]) -> str:
    """
    以「高分片段」直接拼接成中文 Prompt 上下文。
    """
    context = "\n---（片段分隔）---\n".join([c["text"] for c in top_chunks])
    prompt = f"""
你是一個樂於助人的助手。
請僅根據下面提供的「高分片段」回答問題。
若在片段中找不到答案，請回答「我不知道」。

問題：{query}

高分片段（已重排）：
{context}

請用完整句子作答：
"""
    return prompt.strip()


def main():
    parser = argparse.ArgumentParser(description="從 reranked.json 讀取重排結果，做 Chunk Ranking 上下文組裝。")
    parser.add_argument("--in", dest="in_path", default=DEFAULT_IN_PATH, help="輸入檔（預設：reranked.json）")
    parser.add_argument("--top-n", dest="top_n", type=int, default=3, help="取前 N 篇文件來切片段（預設：3）")
    parser.add_argument("--chunk-size", dest="chunk_size", type=int, default=180, help="每個片段的字元數（預設：180）")
    parser.add_argument("--overlap", dest="overlap", type=int, default=40, help="片段之間的重疊字元數（預設：40）")
    parser.add_argument("--top-chunks", dest="top_chunks", type=int, default=3, help="最終取前 M 個高分片段（預設：3）")
    parser.add_argument("--model", dest="model_name", default=DEFAULT_MODEL, help="Cross-Encoder 模型名稱")
    parser.add_argument("--batch-size", dest="batch_size", type=int, default=8, help="推論批次大小（預設：8）")
    parser.add_argument("--max-length", dest="max_length", type=int, default=256, help="最大 token 長度（預設：256）")
    args = parser.parse_args()

    # 讀取前 N 篇重排後的文件
    query, docs, items = load_reranked(args.in_path, top_n=args.top_n)

    # 顯示原始將用到的文件與分數
    print("=== 將使用的前 N 篇文件（重排序後）===")
    for i, it in enumerate(items, 1):
        re = it.get("reranker_score", None)
        ret = it.get("retriever_score", None)
        idx = it.get("idx", None)
        print(f"[{i:02d}] re={re:.4f} | ret={ret:.4f} | idx={idx} | {it['text']}")

    # 建立 chunks
    chunks = build_chunks(docs, chunk_size=args.chunk_size, overlap=args.overlap)
    print(f"\n已切出 {len(chunks)} 個片段（chunk_size={args.chunk_size}, overlap={args.overlap}）")

    # 為每個 chunk 打分
    device = pick_device()
    print(f"開始評分片段（裝置：{device}，模型：{args.model_name}）...")
    scored_chunks = score_chunks_with_ce(
        query=query,
        chunks=chunks,
        model_name=args.model_name,
        device=device,
        batch_size=args.batch_size,
        max_len=args.max_length,
    )

    # 依分數排序並取前 M 個
    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    top_chunks = scored_chunks[: args.top_chunks]

    # 顯示前 M 個高分片段（含來源文件與片段編號）
    print("\n=== 最高分的片段（由高到低）===")
    for i, c in enumerate(top_chunks, 1):
        print(f"[{i:02d}] score={c['score']:.4f} | doc#{c['doc_id']} chunk#{c['chunk_id']} | {c['text']}")

    # 組裝中文 Prompt
    prompt = build_prompt_from_top_chunks(query, top_chunks)
    print("\n=== （Chunk Ranking）組裝後的提示詞 ===\n")
    print(prompt)


if __name__ == "__main__":
    main()
