# retriever_faiss_demo.py
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from huggingface_hub import snapshot_download
from tqdm import tqdm
import os

# ----- 測試資料集 -----
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
QUERY = "公司的總部在哪裡？"
TOP_K = 5
EMB_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
OUT_PATH = "candidates.json"
# -------------------

def download_with_progress(model_name: str) -> str:
    """
    下載 HuggingFace 模型（帶 tqdm 進度條）。
    第一次會下載，之後會直接使用本地快取。
    """
    local_dir = os.path.join("models", model_name.replace("/", "_"))
    if not os.path.exists(local_dir):
        print(f"🔽 正在下載模型: {model_name}")
        snapshot_download(
            repo_id=model_name,
            local_dir=local_dir,
            resume_download=True,
            tqdm_class=tqdm
        )
    else:
        print(f"✅ 已找到本地模型: {local_dir}")
    return local_dir


if __name__ == "__main__":
    print("使用模型進行嵌入 (embedding):", EMB_MODEL_NAME)

    # 確保模型存在（會下載或直接讀本地）
    local_model_path = download_with_progress(EMB_MODEL_NAME)
    embed_model = SentenceTransformer(local_model_path)

    # ----- 文件與查詢向量化 -----
    doc_embeds = embed_model.encode(DOCS, convert_to_numpy=True, normalize_embeddings=True)
    q_embed = embed_model.encode([QUERY], convert_to_numpy=True, normalize_embeddings=True)

    # 使用內積（normalize 後等同於 cosine 相似度）
    dim = doc_embeds.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(doc_embeds.astype("float32"))

    D, I = index.search(q_embed.astype("float32"), TOP_K)
    idxs = I[0].tolist()
    scores = D[0].tolist()

    candidates = [
        {"rank": r + 1, "idx": i, "text": DOCS[i], "retriever_score": float(s)}
        for r, (i, s) in enumerate(zip(idxs, scores))
    ]

    print(f"\n查詢 (Query): {QUERY}\n")
    print("=== 檢索器 (Retriever) Top-K 結果（未重排）===")
    for c in candidates:
        print(f"[R{c['rank']:02d}] 分數={c['retriever_score']:.4f} | idx={c['idx']} | {c['text']}")

    payload = {"query": QUERY, "candidates": candidates}
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"\n已輸出候選結果到 {OUT_PATH}（包含 query 與 Top-{TOP_K} 候選）")
