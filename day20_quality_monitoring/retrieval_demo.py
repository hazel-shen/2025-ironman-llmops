# -*- coding: utf-8 -*-
# retrieval_demo.py
"""
Retrieval-based Check Demo (+ verbose logging)
用 sentence-transformers 計算回答與檢索片段的語義相似度，低於閾值即視為可能幻覺
"""

from typing import List, Optional
from sentence_transformers import SentenceTransformer, util
import torch
import logging
import time
import argparse
import os


# -------- Logging 設定 --------
def setup_logger(verbose: bool = True) -> logging.Logger:
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger("retrieval_demo")
    return logger


class RetrievalChecker:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("retrieval_demo")
        self.logger.info(f"[Init] Loading embedding model: {model_name} ...")
        t0 = time.perf_counter()
        self.model = SentenceTransformer(model_name)
        t1 = time.perf_counter()
        self.logger.info(f"[Init] Model loaded in {t1 - t0:.2f}s")

    def faithfulness_score(self, docs: List[str], answer: str) -> float:
        self.logger.info(f"[Encode] Encoding {len(docs)} doc chunk(s) ...")
        t0 = time.perf_counter()
        # 建議：normalize_embeddings=True 讓餘弦相似度更穩定
        doc_embeds = self.model.encode(docs, convert_to_tensor=True, normalize_embeddings=True)
        t1 = time.perf_counter()
        self.logger.info(f"[Encode] Docs encoded in {t1 - t0:.2f}s | shape={tuple(doc_embeds.shape)}")

        self.logger.info("[Encode] Encoding answer ...")
        t2 = time.perf_counter()
        ans_embed = self.model.encode([answer], convert_to_tensor=True, normalize_embeddings=True)
        t3 = time.perf_counter()
        self.logger.info(f"[Encode] Answer encoded in {t3 - t2:.2f}s | shape={tuple(ans_embed.shape)}")

        self.logger.info("[Score ] Computing cosine similarities ...")
        cos_sim = util.cos_sim(ans_embed, doc_embeds)  # shape: [1, N]
        max_sim = float(cos_sim.max())
        self.logger.info(f"[Score ] max cosine similarity = {max_sim:.4f}")
        return max_sim


# 建議：多語模型（也可改成 bge-m3、jina-embeddings 等）
def retrieval_check(
    answer: str,
    docs: List[str],
    threshold: float = 0.6,
    model_name: str = "all-MiniLM-L6-v2",
    logger: Optional[logging.Logger] = None,
) -> Optional[float]:
    """
    回傳分數（>= threshold）代表通過；否則回傳 None。
    """
    checker = RetrievalChecker(model_name, logger=logger)
    score = checker.faithfulness_score(docs, answer)
    logger and logger.info(f"[Gate  ] threshold={threshold:.2f} → {'PASS' if score >= threshold else 'FAIL'}")
    return score if score >= threshold else None


if __name__ == "__main__":
    # CLI 參數（可選）
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default=os.getenv("EMB_MODEL", "all-MiniLM-L6-v2"), help="embedding model name")
    parser.add_argument("--threshold", type=float, default=float(os.getenv("THRESHOLD", 0.6)))
    parser.add_argument("--quiet", action="store_true", help="suppress info logs")
    args = parser.parse_args()

    logger = setup_logger(verbose=not args.quiet)

    torch.set_num_threads(1)  # 避免執行緒過多
    logger.info("[Start] Retrieval-based hallucination check demo")

    # 檢索到的文件片段（RAG context）
    docs = [
        "公司 VPN 設定文件：步驟 1 安裝軟體，步驟 2 設定帳號，步驟 3 連線。",
    ]
    logger.info(f"[Data ] Loaded {len(docs)} doc chunk(s)")

    # ✅ 合理（非幻覺）對照
    grounded_answer = (
        "依文件步驟：先安裝 VPN 軟體，以公司帳號登入後再嘗試連線。"
        "若需要詳細設定，請參考 IT 提供的安裝指南頁面。"
    )

    # ❌ 幻覺範例（編造路徑/IP/指令，文件未提及）
    hallucinated_answer = (
        "請編輯 /etc/vpn/config，把伺服器設為 10.0.0.5，"
        "存檔後執行 vpnctl --force 重啟即可。"
    )

    # 門檻：可依場景調整
    # FAQ/一般客服：0.4–0.6；內部知識查詢：0.6–0.7；醫療/金融：>=0.8
    threshold = args.threshold
    logger.info(f"[Config] model={args.model} | threshold={threshold:.2f}")

    for label, answer in [
        ("範例 A（合理對照）", grounded_answer),
        ("範例 B（幻覺範例）", hallucinated_answer),
    ]:
        logger.info(f"[Case ] {label}")
        score = retrieval_check(answer, docs, threshold=threshold, model_name=args.model, logger=logger)
        if score is None:
            print(
                f"{label} → Retrieval-based：相似度低於門檻（thr={threshold:.2f}）→ ⚠️ 可能幻覺\n"
                f"回答：{answer}\n"
            )
        else:
            print(
                f"{label} → Retrieval-based：相似度 {score:.2f}（thr={threshold:.2f}）✅\n"
                f"回答：{answer}\n"
            )

    logger.info("[Done ] Demo finished")
