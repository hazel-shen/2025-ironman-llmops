import time
import os
import torch
import torch.nn.functional as F
import numpy as np
from sentence_transformers import CrossEncoder
from openai import OpenAI
from dotenv import load_dotenv

# 全域設定
os.environ["TOKENIZERS_PARALLELISM"] = "false"
torch.set_default_dtype(torch.float32)

# 載入 .env 裡的 OPENAI_API_KEY
load_dotenv()
client = OpenAI()

# 測試資料
QUERY = "公司的總部在哪裡？"
DOCS = [
    # 正確答案
    "本公司總部位於台北市信義區松高路 11 號。",
    # 背景資訊
    "公司創立於 2012 年，專注雲端與資料服務。",
    "我們在新加坡、東京與舊金山設有分公司據點。",
    # 混淆干擾
    "總部附近交通：捷運市政府站步行 5 分鐘可達。",
    "總部附近有一間 Starbucks 咖啡廳，常有員工聚會。",
    "公司每年會在台北 101 舉辦年會。",
    # 無關雜訊
    "請假制度：員工需提前一天申請，緊急情況可事後補辦。",
    "客戶成功部門負責售後導入與教育訓練。",
    "年度目標：拓展東南亞市場並優化資料平台。",
]

# HuggingFace 模型清單
HF_MODELS = [
    "BAAI/bge-reranker-v2-m3",
    "cross-encoder/ms-marco-MiniLM-L-12-v2"
]

def run_hf_reranker(model_name, query, docs):
    """執行 HuggingFace Reranker"""
    model = CrossEncoder(
        model_name,
        device="cuda" if torch.cuda.is_available() else "cpu",
        model_kwargs={"dtype": torch.float32}
    )
    pairs = [(query, d) for d in docs]
    start = time.time()

    # 預設用 list (避免 detach error)
    raw_scores = model.predict(pairs, convert_to_numpy=True)

    # 轉成 numpy array
    scores = np.array(raw_scores, dtype=np.float32)

    # MiniLM 是二分類 relevance 模型，需要 sigmoid
    if "MiniLM" in model_name:
        scores = 1 / (1 + np.exp(-scores))  # sigmoid

    # NaN fallback
    if np.isnan(scores).any():
        print(f"[warn] {model_name} 出現 NaN，分數設為 0")
        scores = np.nan_to_num(scores, nan=0.0)

    elapsed = time.time() - start
    ranking = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
    return ranking, elapsed

def run_openai_reranker(query, docs):
    """執行 OpenAI GPT Reranker (模擬 CrossEncoder 輸出)"""
    start = time.time()
    scores = []
    for d in docs:
        prompt = f"請判斷以下文件與問題的相關性（1~5分）：\n\n問題: {query}\n文件: {d}\n\n只輸出一個數字分數。"
        resp = client.responses.create(
            model="gpt-4o-mini",
            input=prompt
        )
        try:
            score = float(resp.output_text.strip())
        except Exception:
            score = 0.0
        scores.append(score)

    elapsed = time.time() - start
    ranking = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
    return ranking, elapsed

def main():
    print(f"查詢: {QUERY}\n")

    # HuggingFace 模型
    for model_name in HF_MODELS:
        ranking, elapsed = run_hf_reranker(model_name, QUERY, DOCS)
        print(f"=== {model_name} ===")
        for i, (doc, score) in enumerate(ranking[:3], 1):
            print(f"Top{i}: {doc} (score={score:.4f})")
        print(f"耗時: {elapsed:.2f} 秒\n")

    # OpenAI GPT-4o-mini
    ranking, elapsed = run_openai_reranker(QUERY, DOCS)
    print(f"=== OpenAI GPT-4o-mini ===")
    for i, (doc, score) in enumerate(ranking[:3], 1):
        print(f"Top{i}: {doc} (score={score:.2f})")
    print(f"耗時: {elapsed:.2f} 秒\n")

if __name__ == "__main__":
    main()
