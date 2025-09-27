# metadata_comparison.py
import os, hashlib, json
from datetime import datetime

META_FILE = "worker_manual.meta.json"
FILE_PATH = "worker_manual.pdf"

def get_file_hash(path: str) -> str:
    """計算檔案 MD5 hash"""
    hash_md5 = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def format_time(timestamp: float) -> str:
    """格式化時間戳"""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

def check_file(path: str):
    if not os.path.exists(path):
        print(f"❌ 找不到檔案: {path}")
        return

    # 取得目前 metadata
    current_time = os.path.getmtime(path)
    current_hash = get_file_hash(path)

    current_meta = {
        "mtime": current_time,
        "mtime_str": format_time(current_time),
        "hash": current_hash,
    }

    # 如果有舊的 meta，就比對
    if os.path.exists(META_FILE):
        with open(META_FILE, "r", encoding="utf-8") as f:
            old_meta = json.load(f)

        print(f"📂 檔案: {path}")
        print(f"  - 之前修改時間: {format_time(old_meta['mtime'])}")
        print(f"  - 之前 Hash: {old_meta['hash']}")
        print(f"  - 目前修改時間: {current_meta['mtime_str']}")
        print(f"  - 目前 Hash: {current_meta['hash']}")

        if old_meta["hash"] != current_meta["hash"]:
            print("⚠️ 檔案內容已變更，需要更新知識庫！")
        else:
            print("✅ 檔案內容無變更。")

    else:
        print("📥 第一次建立 metadata 紀錄。")

    # 更新 meta 檔案
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(current_meta, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    check_file(FILE_PATH)
