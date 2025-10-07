# scripts/add_docs.py
import os, json, uuid, argparse, hashlib, sys
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

DATA_DIR = "data"
INDEX_PATH = os.path.join(DATA_DIR, "kb.index")
KB_PATH = os.path.join(DATA_DIR, "kb.jsonl")
MAP_PATH = os.path.join(DATA_DIR, "mappings.json")
META_PATH = os.path.join(DATA_DIR, "kb_meta.json")

DIM = 384
MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"


def norm_text(s: str) -> str:
    # 最簡 normalization：去首尾空白、壓縮連續空白
    return " ".join(s.strip().split())


def text_hash(s: str) -> str:
    return hashlib.sha256(norm_text(s).encode("utf-8")).hexdigest()


def load_index():
    if os.path.exists(INDEX_PATH):
        print("🗂️  載入既有索引 ...")
        return faiss.read_index(INDEX_PATH)
    print("🆕  建立新索引 ...")
    return faiss.IndexFlatL2(DIM)


def load_existing_hashes():
    hashes = set()
    if os.path.exists(KB_PATH):
        with open(KB_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                o = json.loads(line)
                h = o.get("text_hash") or text_hash(o["text"])
                hashes.add(h)
    return hashes


def rebuild_rowid_mapping():
    row_map = {}
    with open(KB_PATH, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if not line.strip():
                continue
            o = json.loads(line)
            row_map[str(idx)] = o["doc_id"]
    return row_map


def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def main(args):
    # 收集輸入文本
    new_texts = []
    if args.text:
        new_texts.extend(args.text)
    if args.jsonl:
        with open(args.jsonl, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                o = json.loads(line)
                t = o["text"] if isinstance(o, dict) else str(o)
                new_texts.append(t)

    # 若沒提供，預設示例（只在第一次試跑時方便）
    if not new_texts:
        new_texts = [
            "2025 年 VPN 設定流程：步驟 1 下載新版客戶端，步驟 2 使用 SSO 登入。",
            "新的人資政策：試用期滿後方可申請遠端辦公。",
        ]
        print("ℹ️ 未指定輸入，使用預設示例兩筆。下次可用 -t/--text 或 --jsonl 指定。")

    # 去重：比對既有雜湊
    existing = load_existing_hashes()
    to_add = []
    skipped = 0
    for t in new_texts:
        h = text_hash(t)
        if h in existing:
            skipped += 1
            continue
        to_add.append((t, h))
        existing.add(h)

    if not to_add:
        print(f"✅ 無需新增：全部 {len(new_texts)} 筆皆為重複（已存在）。")
        return

    # 1) 索引
    index = load_index()

    # 2) 向量化
    print(f"🧠  載入嵌入模型：{MODEL_ID}")
    model = SentenceTransformer(MODEL_ID)
    texts_only = [t for t, _ in to_add]
    print(f"🔢  向量化 {len(texts_only)} 筆文本 ...")
    vecs = model.encode(texts_only, normalize_embeddings=True, show_progress_bar=True)
    vecs = np.asarray(vecs, dtype="float32")

    # 3) 寫入索引
    print("📌  寫入索引 ...")
    index.add(vecs)
    faiss.write_index(index, INDEX_PATH)

    # 4) 追加原文（含 text_hash）
    print("📝  追加原文 ...")
    with open(KB_PATH, "a", encoding="utf-8") as f:
        for t, h in to_add:
            doc_id = f"doc_{uuid.uuid4().hex[:8]}"
            f.write(json.dumps({"doc_id": doc_id, "text": t, "text_hash": h}, ensure_ascii=False) + "\n")

    # 5) 更新映射
    print("🔗  更新 rowid 對應 ...")
    mappings = {"rowid_to_doc_id": rebuild_rowid_mapping()}
    save_json(MAP_PATH, mappings)

    # 6) 更新中繼資料
    print("🧾  更新 KB meta ...")
    meta = json.load(open(META_PATH, encoding="utf-8"))
    meta["kb_version"] += 1
    meta["doc_count"] = len(mappings["rowid_to_doc_id"])
    save_json(META_PATH, meta)

    print(f"✅ 完成：新增 {len(to_add)} 筆；跳過重複 {skipped} 筆；kb_version={meta['kb_version']}；總筆數={meta['doc_count']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-t", "--text", action="append", help="直接新增一段文本；可重複指定多次")
    ap.add_argument("--jsonl", type=str, help="從 jsonl 檔新增，格式：每行一個物件，至少含 text 欄位")
    args = ap.parse_args()
    main(args)
