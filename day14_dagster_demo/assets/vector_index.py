import json
import os
from datetime import datetime
from typing import List
from dagster import asset
from .common import INDEX_FILE, RAW_FILE, DATA_DIR

# 📄 資產：vector_index
# 功能：把 chunks + vectors 整合成索引 (JSON)，方便檢索使用
@asset(description="輸出 data/vector_index.json")
def vector_index(context, chunks: List[str], vectors: List[List[float]]) -> str:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if len(chunks) != len(vectors):
        raise ValueError(f"chunks ({len(chunks)}) 與 vectors ({len(vectors)}) 數量不一致")

    out = {
        "meta": {
            "source": str(RAW_FILE.name),
            "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "model": os.getenv("QUERY_EMBEDDING_MODEL", "text-embedding-3-small"),
        },
        "items": [
            {"id": i, "chunk": c, "vector": v}
            for i, (c, v) in enumerate(zip(chunks, vectors))
        ],
    }

    INDEX_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    context.log.info(f"索引已寫入：{INDEX_FILE}")
    return str(INDEX_FILE)
