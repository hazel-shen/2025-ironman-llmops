#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
02_faiss_minimal_flat.py
多文件版：文件 → 向量 → FAISS Flat(L2) → 查詢

特色：
- 內建 12 條混合文件（人資/財務/干擾內容），更能看出檢索效果
- 以 L2 距離檢索（距離越小越相似）
- 支援從命令列覆寫查詢字串：python 02_faiss_minimal_flat.py "我要請病假"
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

DOCS = [
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

def pretty_print_results(query: str, docs: list[str], indices: np.ndarray, dists: np.ndarray, k: int = TOP_K) -> None:
    print("\n" + "═" * 60)
    print(f"【查詢】{query}")
    print(f"【Top {k} 結果｜距離越小越相關】")
    print("─" * 60)
    for rank, (i, d) in enumerate(zip(indices[:k], dists[:k]), start=1):
        print(f"{rank:>2}. 距離={d:.4f} | #{i:02d} | {docs[i]}")
    print("═" * 60)

def main() -> None:
    # 讓 FAISS 在 macOS/Arm 上更穩定（非必要，但建議保留）
    faiss.omp_set_num_threads(1)

    # 讀取 API Key
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("沒有找到 OPENAI_API_KEY，請在 .env 設定！")

    client = OpenAI(api_key=api_key)

    # 顯示文件清單
    print("【文件清單】")
    for i, d in enumerate(DOCS):
        print(f"{i:02d}: {d}")

    # 向量化（示範簡單逐筆；若大量文件，建議改成 batch 版本）
    print("\n正在產生文件向量（embedding）...")
    embs = []
    for d in DOCS:
        emb = client.embeddings.create(model=EMBED_MODEL, input=d).data[0].embedding
        embs.append(emb)
    embs = np.array(embs, dtype="float32")

    # 顯示向量維度
    dim = embs.shape[1]
    print(f"Embedding 維度：{dim}（模型：{EMBED_MODEL}）")
    print("第一個文件向量前 8 維：", np.round(embs[0][:8], 4))

    # 建立 FAISS Flat (L2) 索引
    index = faiss.IndexFlatL2(dim)
    index.add(embs)

    # 讀取查詢字串（可由命令列帶入）
    query = sys.argv[1] if len(sys.argv) > 1 else "我要報銷 2000 元"

    # 產生查詢向量並檢索
    q = client.embeddings.create(model=EMBED_MODEL, input=query).data[0].embedding
    q = np.array([q], dtype="float32")

    D, I = index.search(q, k=min(TOP_K, len(DOCS)))
    dists, idxs = D[0], I[0]

    # 顯示結果
    pretty_print_results(query, DOCS, idxs, dists, k=min(TOP_K, len(DOCS)))

    # 參考：與「Naive 全量比較」對照（驗證正確性）
    # （Flat 索引與全量 L2 計算理論上結果應一致）
    naive = np.array([norm(q[0] - v) for v in embs], dtype="float32")
    naive_order = naive.argsort()[: min(TOP_K, len(DOCS))]
    if not np.array_equal(naive_order, idxs[: len(naive_order)]):
        print("\n⚠️ 提示：FAISS 與 Naive 排序不同，請檢查向量或索引設定。")
    else:
        print("\n✅ 驗證：FAISS 與 Naive(L2) 排序一致。")

if __name__ == "__main__":
    main()
