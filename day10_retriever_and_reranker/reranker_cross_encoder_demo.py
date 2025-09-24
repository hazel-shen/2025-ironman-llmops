# reranker_cross_encoder_demo.py
import json
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

IN_PATH = "candidates.json"
OUT_PATH = "reranked.json"
CE_MODEL_NAME = "BAAI/bge-reranker-v2-m3"

def load_candidates(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["query"], data["candidates"]

def rerank(query, texts, model_name=CE_MODEL_NAME, batch_size=8, max_len=256):
    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.eval()

    scores = []
    with torch.no_grad():
        for start in range(0, len(texts), batch_size):
            batch_docs = texts[start:start + batch_size]
            inputs = tok(
                [query] * len(batch_docs),
                batch_docs,
                padding=True,
                truncation=True,
                max_length=max_len,
                return_tensors="pt",
            )
            logits = model(**inputs).logits.squeeze(-1)  # (batch_size,)
            scores.extend(logits.cpu().tolist())
    return scores

def main():
    query, candidates = load_candidates(IN_PATH)
    print(f"查詢 (Query): {query}\n")

    print("=== 檢索器 (Retriever) Top-K（原始順序）===")
    for c in candidates:
        print(f"[R{c['rank']:02d}] ret={c['retriever_score']:.4f} | idx={c['idx']} | {c['text']}")

    texts = [c["text"] for c in candidates]
    re_scores = rerank(query, texts)

    merged = []
    for c, re_s in zip(candidates, re_scores):
        merged.append({
            **c,
            "reranker_score": float(re_s),
        })

    # 依 Reranker 分數排序
    reranked = sorted(merged, key=lambda x: x["reranker_score"], reverse=True)

    print("\n=== 重排序器 (Reranker) Top-3 ===")
    for i, c in enumerate(reranked[:3], 1):
        print(f"[R*{i:02d}] re={c['reranker_score']:.4f} | ret={c['retriever_score']:.4f} | idx={c['idx']} | {c['text']}")

    print("\n=== 完整對照：retriever vs reranker ===")
    for i, c in enumerate(reranked, 1):
        print(f"[{i:02d}] re={c['reranker_score']:.4f} | ret={c['retriever_score']:.4f} | idx={c['idx']} | {c['text']}")

    # 輸出結果到 reranked.json，day11 會用到
    out_payload = {
        "query": query,
        "model": CE_MODEL_NAME,
        "retriever": candidates,   # 原始候選（保留原 rank 與 retriever_score）
        "reranked": reranked,      # 重排後（含 reranker_score 與新 rerank_rank）
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out_payload, f, ensure_ascii=False, indent=2)

    print(f"\n已輸出重排結果到 {OUT_PATH}")
if __name__ == "__main__":
    main()
