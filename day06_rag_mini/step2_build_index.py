# step2_build_index.py
import json
import numpy as np
import faiss
from pathlib import Path
from utils_openai import embed, EMBED_MODEL # 呼叫 OpenAI 的工具模組

DATA_PATH = Path("data/docs.json")
INDEX_DIR = Path("index")

def main():
    # 1) 載入 step1 建立的文件
    docs = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    # 2) 先算第一個 embedding 取得維度
    first_vec = np.array(embed(docs[0]), dtype="float32")
    d = first_vec.shape[0]
    index = faiss.IndexFlatL2(d)

    # 3) 全量轉 embedding 並加入索引
    all_vecs = [first_vec] + [np.array(embed(t), dtype="float32") for t in docs[1:]]
    mat = np.vstack(all_vecs)  # (N, d)
    index.add(mat)

    # 4) 輸出索引與中繼資料
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_DIR / "faiss.index"))
    meta = {
        "model": EMBED_MODEL,
        "dim": int(d),
        "docs": docs
    }
    (INDEX_DIR / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 建索引完成：{len(docs)} 篇，維度 {d}")

if __name__ == "__main__":
    main()
