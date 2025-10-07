# scripts/pack_and_register.py
import os, json, tarfile, hashlib, argparse, time, sys
import requests

DATA_DIR = "data"
INDEX_PATH = os.path.join(DATA_DIR, "kb.index")
KB_PATH = os.path.join(DATA_DIR, "kb.jsonl")
MAP_PATH = os.path.join(DATA_DIR, "mappings.json")
META_PATH = os.path.join(DATA_DIR, "kb_meta.json")

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()

def pack_kb(out_tar):
    files = [INDEX_PATH, KB_PATH, MAP_PATH, META_PATH]
    missing = [p for p in files if not os.path.exists(p)]
    if missing:
        print("❌ 找不到以下檔案，請先 `make add` 產生索引與資料：\n  " + "\n  ".join(missing))
        sys.exit(2)
    with tarfile.open(out_tar, "w:gz") as tar:
        for p in files:
            tar.add(p, arcname=os.path.basename(p))
    return sha256_file(out_tar)

def register_kb(registry_url: str, name: str, version: str, artifact_url: str, meta: dict, tags=None):
    payload = {
        "version": version,
        "artifact_url": artifact_url,
        "tags": tags or ["kb","rag","incremental"],
        "meta": {
            "artifact_type": "KnowledgeBase",
            "embedding_model": meta.get("model"),
            "dim": meta.get("dim", 384),
            "doc_count": meta.get("doc_count", 0),
            "kb_version": meta.get("kb_version"),
            "index_type": "faiss.IndexFlatL2",
            "hash": meta.get("hash"),
        }
    }
    r = requests.post(f"{registry_url}/models/{name}/versions", json=payload, timeout=10)
    # 友善輸出
    try:
        r.raise_for_status()
        print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    except requests.HTTPError:
        body = None
        try:
            body = r.json()
        except Exception:
            body = r.text
        print("❌ Registry Error", r.status_code)
        print("Response:", json.dumps(body, ensure_ascii=False, indent=2) if isinstance(body, dict) else body)
        print("Payload:", json.dumps(payload, ensure_ascii=False, indent=2))
        sys.exit(1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", type=str, default="http://localhost:8000")
    ap.add_argument("--name", type=str, default="faq-bot")
    ap.add_argument("--pack-only", action="store_true")
    ap.add_argument("--version", type=str, default=None, help="覆寫版本字串（例如 4-kb+exp1）")
    ap.add_argument("--auto-unique", action="store_true", help="未指定版本時在尾端加時間戳避免重複")
    args = ap.parse_args()

    meta = json.load(open(META_PATH, encoding="utf-8"))
    ts = int(time.time())
    out_tar = os.path.join(DATA_DIR, f"kb-v{ts}.tar.gz")
    checksum = pack_kb(out_tar)

    artifact_url = f"file://{os.path.abspath(out_tar)}"
    meta["hash"] = checksum
    print(f"✅ 已打包：{out_tar}\n   checksum: {checksum}\n   artifact_url: {artifact_url}")

    if args.pack_only:
        return

    version = args.version or f"{meta['kb_version']}-kb" + (f"+{ts}" if args.auto_unique else "")
    register_kb(args.registry, args.name, version, artifact_url, meta)

if __name__ == "__main__":
    main()
