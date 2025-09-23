#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
03_faiss_compare_cosine.py
對照實驗台：Naive vs FAISS、L2 vs Cosine

功能：
- 在相同文件與查詢下，同步比較四種檢索模式：
  1) Naive 全量 L2
  2) FAISS IndexFlatL2
  3) Naive 全量 Cosine（需 L2 normalize）
  4) FAISS IndexFlatIP（Cosine 需先 normalize）
- 顯示 Top-K、距離/相似度、與排序一致性檢查

用法：
    python 03_faiss_compare_cosine.py
    python 03_faiss_compare_cosine.py "我要請病假"

備註：
- Cosine 相似度 = 內積(單位向量)。因此需先對向量做 L2 normalize。
- 為了讀者可重現，預設用 12 筆 DOCS；如需更大資料量，將 USE_BIG_DOCS=True。
"""

from __future__ import annotations
import os
import sys
import faiss
import numpy as np
from numpy.linalg import norm
from dotenv import load_dotenv
from openai import OpenAI

EMBED_MODEL = "text-embedding-3-small"
TOP_K = 5
USE_BIG_DOCS = False  # 想用 60 筆文件就設為 True（等同 02b 的集合）

DOCS_SMALL = [
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
    "伺服器維護時間為每週日凌晨 2 點到 4 點",
    "資料庫備份需至少保存 90 天",
]

DOCS_BIG = (DOCS_SMALL + [
    "VPN 連線需啟用 MFA 驗證",
    "內部系統登入錯誤超過五次會被鎖定",
    "程式碼需經過 Code Review 才能合併",
    "重要檔案需加密後才能寄送",
    "密碼至少需包含 12 個字元，且含大小寫與符號",
    "員工離職後帳號需在 24 小時內停用",
    "禁止使用未授權的雲端服務儲存公司資料",
    "所有筆電需安裝防毒軟體並保持更新",
    # 干擾句
    "台北 101 是全台最高的摩天大樓",
    "火鍋是冬天最受歡迎的料理之一",
    "這間咖啡廳的拿鐵特別好喝",
    "小美最近在學習日語",
]) * 2  # 複製一份 → 大約 48 筆；再視需要增減

def batch_embed(client: OpenAI, texts: list[str], batch_size: int = 32) -> np.ndarray:
    """簡單的 batch embedding。"""
    out = []
    for i in range(0, len(texts), batch_size):
        resp = client.embeddings.create(model=EMBED_MODEL, input=texts[i:i+batch_size])
        out.extend([d.embedding for d in resp.data])
    return np.array(out, dtype="float32")

def l2_normalize(x: np.ndarray) -> np.ndarray:
    x = x.copy()
    faiss.normalize_L2(x)
    return x

def print_block(title: str, docs: list[str], idxs: np.ndarray, scores: np.ndarray, is_similarity: bool, k: int):
    print("\n" + "═" * 70)
    print(f"【{title}】Top {k}（{'分數越大越相似' if is_similarity else '距離越小越相似'}）")
    print("─" * 70)
    for r, (i, s) in enumerate(zip(idxs[:k], scores[:k]), 1):
        print(f"{r:>2}. {'score' if is_similarity else 'dist'}={s:.4f} | #{i:03d} | {docs[i]}")
    print("═" * 70)

def main():
    # 保守執行緒，避免 macOS/Arm 上的 OMP 行為不穩定
    faiss.omp_set_num_threads(1)

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("沒有找到 OPENAI_API_KEY，請在 .env 設定！")
    client = OpenAI(api_key=api_key)

    docs = DOCS_BIG if USE_BIG_DOCS else DOCS_SMALL
    print(f"【文件總數】{len(docs)}")
    for i, d in enumerate(docs[:min(5, len(docs))]):
        print(f"{i:03d}: {d}")

    # 產生文件向量
    print("\n正在產生文件向量（embedding）...")
    embs = batch_embed(client, docs, batch_size=32)
    dim = embs.shape[1]
    print(f"Embedding 維度：{dim}（模型：{EMBED_MODEL}）")

    # 查詢字串
    query = sys.argv[1] if len(sys.argv) > 1 else "我要報銷 2000 元"
    q = client.embeddings.create(model=EMBED_MODEL, input=query).data[0].embedding
    q = np.array(q, dtype="float32")

    # ------- A) L2 距離 -------
    # Naive: 全量比對 L2
    dists = np.linalg.norm(embs - q, axis=1)
    naive_l2_order = np.argsort(dists)
    print_block("Naive L2", docs, naive_l2_order, dists[naive_l2_order], is_similarity=False, k=min(TOP_K, len(docs)))

    # FAISS: IndexFlatL2
    index_l2 = faiss.IndexFlatL2(dim)
    index_l2.add(embs)
    D, I = index_l2.search(q.reshape(1, -1), k=min(TOP_K, len(docs)))
    print_block("FAISS L2", docs, I[0], D[0], is_similarity=False, k=min(TOP_K, len(docs)))

    # ------- B) Cosine 相似度（需 normalize） -------
    embs_cos = l2_normalize(embs)
    q_cos = l2_normalize(q.reshape(1, -1))[0]

    # Naive: 以內積為相似度
    sims = embs_cos @ q_cos
    naive_cos_order = np.argsort(-sims)
    print_block("Naive Cosine", docs, naive_cos_order, sims[naive_cos_order], is_similarity=True, k=min(TOP_K, len(docs)))

    # FAISS: IndexFlatIP（IP = inner product）
    index_ip = faiss.IndexFlatIP(dim)
    index_ip.add(embs_cos)
    S, J = index_ip.search(q_cos.reshape(1, -1), k=min(TOP_K, len(docs)))
    print_block("FAISS Cosine (IP)", docs, J[0], S[0], is_similarity=True, k=min(TOP_K, len(docs)))

    # ------- C) 一致性檢查 -------
    def topk_equal(a: np.ndarray, b: np.ndarray, k: int) -> bool:
        return np.array_equal(a[:k], b[:k])

    k = min(TOP_K, len(docs))
    print("\n一致性檢查：")
    print(f"- Naive L2 vs FAISS L2：{'一致 ✅' if topk_equal(naive_l2_order, I[0], k) else '不一致 ⚠️'}")
    print(f"- Naive Cosine vs FAISS Cosine：{'一致 ✅' if topk_equal(naive_cos_order, J[0], k) else '不一致 ⚠️'}")
    print(f"- L2 Top-{k} vs Cosine Top-{k}（Naive）重疊數量：{len(set(naive_l2_order[:k]) & set(naive_cos_order[:k]))}")

if __name__ == "__main__":
    main()
