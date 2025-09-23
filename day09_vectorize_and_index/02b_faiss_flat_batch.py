#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
02b_faiss_flat_batch.py
多文件批次版：文件 → 批次向量化 → FAISS Flat(L2) → 查詢

特色：
- 內建 50+ 條文件（人資 / 財務 / IT / 干擾內容）
- 批次 embedding（一次送 20 筆，避免 API 頻繁呼叫）
- FAISS L2 檢索，TOP_K=5
"""

from __future__ import annotations
import os
import sys
import faiss
import numpy as np
from numpy.linalg import norm
from dotenv import load_dotenv
from openai import OpenAI

TOP_K = 5
EMBED_MODEL = "text-embedding-3-small"
BATCH_SIZE = 20

DOCS = [
    # 人資規章
    "加班申請需事先提出，加班工時可折換補休",
    "出差申請需填寫出差單，並附上行程與預算",
    "報銷規則需要提供發票，金額超過 1000 需經理簽核",
    "員工請假需提前一天提出，病假需附上診斷證明",
    "差旅住宿費上限為每晚 3000 元",
    "年度績效考核結果將影響年終獎金比例",
    "離職需提前一個月提出申請",
    "會議室使用需事先預約，不可長期佔用",
    "公司總部位於台北市信義區",
    "飲料與零食可由團隊經費報支",
    # IT / 安全
    "伺服器維護時間為每週日凌晨 2 點到 4 點",
    "資料庫備份需至少保存 90 天",
    "VPN 連線需啟用 MFA 驗證",
    "內部系統登入錯誤超過五次會被鎖定",
    "程式碼需經過 Code Review 才能合併",
    "重要檔案需加密後才能寄送",
    "密碼至少需包含 12 個字元，且含大小寫與符號",
    "員工離職後帳號需在 24 小時內停用",
    "禁止使用未授權的雲端服務儲存公司資料",
    "所有筆電需安裝防毒軟體並保持更新",
    # 干擾內容
    "台北 101 是全台最高的摩天大樓",
    "小王喜歡在週末去看棒球比賽",
    "這間咖啡廳的拿鐵特別好喝",
    "火鍋是冬天最受歡迎的料理之一",
    "台灣的高山茶很有名",
    "手機需要充電才能使用",
    "今天的天氣很適合去爬山",
    "假日百貨公司人潮眾多",
    "小美最近在學習日語",
    "這部電影獲得了國際獎項",
] * 2  # 複製一份 → 共 60 筆

def batch_embedding(client: OpenAI, texts: list[str], batch_size: int = BATCH_SIZE) -> np.ndarray:
    """批次 embedding，避免 API 頻繁呼叫"""
    all_embeddings: list[np.ndarray] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        resp = client.embeddings.create(model=EMBED_MODEL, input=batch)
        embs = [d.embedding for d in resp.data]
        all_embeddings.extend(embs)
    return np.array(all_embeddings, dtype="float32")

def pretty_print_results(query: str, docs: list[str], indices: np.ndarray, dists: np.ndarray, k: int = TOP_K) -> None:
    print("\n" + "═" * 60)
    print(f"【查詢】{query}")
    print(f"【Top {k} 結果｜距離越小越相關】")
    print("─" * 60)
    for rank, (i, d) in enumerate(zip(indices[:k], dists[:k]), start=1):
        print(f"{rank:>2}. 距離={d:.4f} | #{i:03d} | {docs[i]}")
    print("═" * 60)

def main() -> None:
    faiss.omp_set_num_threads(1)
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("沒有找到 OPENAI_API_KEY，請在 .env 設定！")

    client = OpenAI(api_key=api_key)

    print(f"【文件總數】{len(DOCS)}")
    print("前 5 筆文件：")
    for i, d in enumerate(DOCS[:5]):
        print(f"{i:03d}: {d}")

    print("\n正在批次產生文件向量（embedding）...")
    embs = batch_embedding(client, DOCS, BATCH_SIZE)
    dim = embs.shape[1]
    print(f"Embedding 維度：{dim}（模型：{EMBED_MODEL}）")
    print("第一個文件向量前 8 維：", np.round(embs[0][:8], 4))

    index = faiss.IndexFlatL2(dim)
    index.add(embs)

    query = sys.argv[1] if len(sys.argv) > 1 else "我要請病假"
    q_emb = client.embeddings.create(model=EMBED_MODEL, input=query).data[0].embedding
    q_emb = np.array([q_emb], dtype="float32")

    D, I = index.search(q_emb, k=min(TOP_K, len(DOCS)))
    pretty_print_results(query, DOCS, I[0], D[0], k=min(TOP_K, len(DOCS)))

    # 驗證 Naive L2
    naive = np.array([norm(q_emb[0] - v) for v in embs], dtype="float32")
    naive_order = naive.argsort()[: TOP_K]
    if not np.array_equal(naive_order, I[0][:TOP_K]):
        print("\n⚠️ FAISS 與 Naive 排序不同")
    else:
        print("\n✅ 驗證：FAISS 與 Naive(L2) 排序一致")

if __name__ == "__main__":
    main()
