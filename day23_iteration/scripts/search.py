# scripts/search.py
import os, json, argparse, hashlib
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

DATA_DIR = "data"
INDEX_PATH = os.path.join(DATA_DIR, "kb.index")
KB_PATH = os.path.join(DATA_DIR, "kb.jsonl")
MAP_PATH = os.path.join(DATA_DIR, "mappings.json")
META_PATH = os.path.join(DATA_DIR, "kb_meta.json")

def norm_text(s: str) -> str:
    return " ".join(s.strip().split())

def text_hash(s: str) -> str:
    return hashlib.sha256(norm_text(s).encode("utf-8")).hexdigest()

def load_jsonl(path):
    docs, hashes = {}, {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            obj = json.loads(line)
            t = obj["text"]
            docs[obj["doc_id"]] = t
            hashes[obj["doc_id"]] = obj.get("text_hash") or text_hash(t)
    return docs, hashes

def main(query, k=3):
    if not os.path.exists(INDEX_PATH):
        raise SystemExit("Index not found. Run add_docs.py first.")

    index = faiss.read_index(INDEX_PATH)
    meta = json.load(open(META_PATH, encoding="utf-8"))
    mappings = json.load(open(MAP_PATH, encoding="utf-8"))
    id_map = mappings["rowid_to_doc_id"]
    kb, hashes = load_jsonl(KB_PATH)

    model = SentenceTransformer(meta["model"])
    qv = model.encode([query], normalize_embeddings=True).astype("float32")

    pool_k = min(max(k * 5, k), index.ntotal)  # 拉大候選，用來去重
    D, I = index.search(qv, pool_k)

    print(f"\n🔎 Query: {query}")
    seen, picked = set(), []
    for dist, rowid in zip(D[0], I[0]):
        doc_id = id_map[str(rowid)]
        t = kb[doc_id]
        h = hashes[doc_id]
        if h in seen:
            continue
        seen.add(h)
        sim = 1 - float(dist) / 2
        picked.append((doc_id, t, sim))
        if len(picked) >= k:
            break

    # 顯示前 k 個唯一項目
    for i, (doc_id, t, sim) in enumerate(picked, 1):
        print(f"[{i}] sim={sim:.4f} | {doc_id} | {t}")

    # Context 只用「已挑選」清單（唯一且至多 k 筆）
    ctx = "\n".join(t for _, t, _ in picked)
    print("\n---\n🧩 Context for LLM:\n" + ctx)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query", type=str)
    ap.add_argument("--k", type=int, default=3)
    args = ap.parse_args()
    main(args.query, k=args.k)
