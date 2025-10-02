# services/retrieval_service.py
from typing import List, Tuple
from pathlib import Path
import os, json
import numpy as np
import faiss

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ---- 基本設定 ----
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("沒有找到 OPENAI_API_KEY，請檢查環境變數！")

OPENAI_TIMEOUT = float(os.getenv("OPENAI_TIMEOUT", "20"))
EMBEDDING_MODEL = os.getenv("QUERY_EMBEDDING_MODEL", "text-embedding-3-small")
L2_THRESHOLD = float(os.getenv("L2_THRESHOLD", "1.8"))

client = OpenAI(timeout=OPENAI_TIMEOUT, max_retries=0)

# ---- 知識庫（示範版，和 Day07 相同）----
DOCS = [
    "請假流程：需要先主管簽核，然後到 HR 系統提交。",
    "加班申請：需事先提出，加班工時可折換補休。",
    "報銷規則：需要提供發票，金額超過 1000 需經理簽核。",
    "出差申請：需填寫出差單，並附上行程與預算，送交主管審核。",
    "電腦設備申請：新進員工需向 IT 部門提出申請，並由主管批准。",
    "VPN 使用：連接公司內網必須使用公司發放的 VPN 帳號。",
    "考勤規則：遲到超過 15 分鐘需填寫說明單。",
    "文件管理：重要檔案需存放於公司雲端硬碟，不可存個人電腦。",
    "安全規範：不得將公司機密資料外傳或存放於私人雲端。",
    "年度健檢：每位員工需於 9 月前完成公司指定醫院的健康檢查。"
]

# 也支援從 data/vector_index.json 載入（可選）
INDEX_PATH = Path("data/vector_index.json")

# ---- 內存索引（和 Day07 一樣，啟動時建索引）----
_d = 1536
_index = faiss.IndexFlatL2(_d)
_doc_embeddings = None

def _get_embedding(text: str) -> List[float]:
    return client.embeddings.create(model=EMBEDDING_MODEL, input=text).data[0].embedding

def _ensure_index():
    global _doc_embeddings
    if _index.ntotal == 0:
        if INDEX_PATH.exists():
            # 可選：從檔案載入嵌入（若你前面有離線流程）
            data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
            vectors = [it["vector"] for it in data.get("items", [])]
            _doc_embeddings = np.array(vectors, dtype="float32")
            _index.add(_doc_embeddings)
        else:
            # 直接即時產生（示範）
            _doc_embeddings = np.array([_get_embedding(doc) for doc in DOCS], dtype="float32")
            _index.add(_doc_embeddings)

def retrieve_best(q: str, k: int = 3) -> Tuple[str, float]:
    """回傳最相關片段與距離（若超過門檻則回『知識庫裡沒有相關答案。』）"""
    _ensure_index()
    q_emb = np.array([_get_embedding(q)], dtype="float32")
    D, I = _index.search(q_emb, k)
    best_idx = int(I[0][0])
    best_dist = float(D[0][0])
    if best_dist > L2_THRESHOLD:
        return "知識庫裡沒有相關答案。", best_dist
    if INDEX_PATH.exists():
        # 若從檔案載入，沒有 DOCS 文本，需在 json 內保存 chunk 文字；此處簡化
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        chunk = data["items"][best_idx]["chunk"]
        return chunk, best_dist
    else:
        return DOCS[best_idx], best_dist
