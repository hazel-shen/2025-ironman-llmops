# pipeline.py
from __future__ import annotations
import os
from steps.detect import detect_change, save_hash
from steps.embed import embed_texts
from steps.update_index import write_index
from dotenv import load_dotenv


SRC_FILE = "data/faq.txt"
META_HASH = "artifacts/source.hash"
INDEX_OUT = "artifacts/vector_index.json"

load_dotenv()

def simple_chunk(text: str, max_chars: int = 400) -> list[str]:
    # 極簡切片：依段落與長度切
    parts = []
    for para in text.splitlines():
        if not para.strip():
            continue
        buf = para.strip()
        while len(buf) > max_chars:
            parts.append(buf[:max_chars])
            buf = buf[max_chars:]
        if buf:
            parts.append(buf)
    return parts or ["(空文件)"]

def main() -> None:
    print("🔍 檢查檔案是否變動…")
    res = detect_change(SRC_FILE, META_HASH)
    if not res.changed:
        print("✅ 無變動，跳過更新")
        return

    print("⚠️ 偵測到變動，開始更新索引…")
    with open(SRC_FILE, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = simple_chunk(text)
    print(f"✂️ 切出 {len(chunks)} 個片段")

    vectors = embed_texts(chunks)
    print(f"🧠 產生 {len(vectors)} 筆向量")

    records = [
        {"id": i, "text": chunks[i], "vector": vectors[i]}
        for i in range(len(chunks))
    ]
    write_index(INDEX_OUT, records)
    save_hash(META_HASH, res.new_hash)
    print(f"📦 已寫入索引：{INDEX_OUT}")
    print("🎉 更新完成！")

if __name__ == "__main__":
    # 確保資料夾存在
    os.makedirs("data", exist_ok=True)
    os.makedirs("artifacts", exist_ok=True)
    if not os.path.exists(SRC_FILE):
        with open(SRC_FILE, "w", encoding="utf-8") as f:
            f.write("公司員工手冊 v1.0：\n第二章 加班與補休：加班需事前申請，工時可折換補休。\n")
    main()
