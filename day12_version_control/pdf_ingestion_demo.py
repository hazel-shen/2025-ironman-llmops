# pdf_ingestion_demo.py (robust)
import pdfplumber
import re
import os
from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

# ========== 工具函式 ==========

def clean_text(s: str) -> str:
    """移除多餘空白"""
    return re.sub(r"\s+", " ", s).strip()

def chunk_by_rules(text: str) -> List[str]:
    """
    根據規則切分 PDF 文字：
    - 章節標題 (第X章)
    - 條列 (1. / 2. / 3.)
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    chunks, buf = [], []

    for line in lines:
        # 章節標題：單獨成段
        if line.startswith("第") and "章" in line:
            if buf:
                chunks.append(" ".join(buf))
                buf = []
            buf.append(line)

        # 條列數字：單獨成段
        elif re.match(r"^\d+\.", line):
            if buf:
                chunks.append(" ".join(buf))
                buf = []
            buf.append(line)

        # 其他：接續到當前段
        else:
            buf.append(line)

    if buf:
        chunks.append(" ".join(buf))
    return [clean_text(c) for c in chunks]

def load_pdf(path: str) -> List[str]:
    """從 PDF 載入文字，並依規則切成 chunk（含錯誤處理）"""
    if not os.path.exists(path):
        print(f"❌ 找不到檔案：{path}，請確認路徑是否正確。")
        return []

    docs: List[str] = []
    try:
        with pdfplumber.open(path) as pdf:
            if not pdf.pages:
                print("⚠️ 這個 PDF 沒有任何頁面。")
                return []
            for i, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text()
                except Exception as pe:
                    print(f"⚠️ 第 {i} 頁解析失敗，已略過。原因：{pe}")
                    continue
                if text:
                    docs.extend(chunk_by_rules(text))
                else:
                    print(f"ℹ️ 第 {i} 頁沒有可抽取文字，可能是掃描影像或加密。")
    except Exception as e:
        print(f"⚠️ 開啟或處理 PDF 時發生錯誤：{e}")
        return []

    return docs

def build_index(docs: List[str]) -> Tuple[TfidfVectorizer, NearestNeighbors, List[str]]:
    """
    建立向量索引
    - 使用 char ngram，更適合中文
    - ngram_range=(1,3)：單字、雙字、三字都考慮
    """
    if not docs:
        raise ValueError("沒有可用文件段落可建立索引。")

    vec = TfidfVectorizer(analyzer="char", ngram_range=(1,3))
    X = vec.fit_transform(docs)
    nn = NearestNeighbors(metric="cosine").fit(X)
    return vec, nn, docs

def query(q: str, vec: TfidfVectorizer, nn: NearestNeighbors, docs: List[str], topk: int = 3) -> None:
    """查詢，並回傳最相似的段落"""
    if not docs:
        print("⚠️ 索引為空，無法查詢。")
        return
    qv = vec.transform([q])
    k = min(topk, len(docs))
    dist, idx = nn.kneighbors(qv, n_neighbors=k)
    print(f"\nQ: {q}")
    for d, i in zip(dist[0], idx[0]):
        print(f"- {docs[i]} (score={1-d:.4f})")

# ========== 主程式 ==========

if __name__ == "__main__":
    pdf_path = "worker_manual.pdf"  # 換成要處理的 PDF 檔案路徑
    docs = load_pdf(pdf_path)

    if not docs:
        print("⚠️ 沒有載入任何段落，請確認 PDF 是否有效或可抽取文字。")
    else:
        print(f"✅ 載入完成，共 {len(docs)} 段落")
        try:
            vec, nn, docs = build_index(docs)
        except Exception as e:
            print(f"⚠️ 建立索引失敗：{e}")
        else:
            # 範例查詢
            query("請假規則", vec, nn, docs)
            query("加班", vec, nn, docs)
            query("報銷", vec, nn, docs)
