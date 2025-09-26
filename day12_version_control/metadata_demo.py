# metadata_demo.py
import hashlib
import json
import os
from datetime import datetime

META_FILE = "metadata.json"

def calc_hash(path):
    """計算檔案的 SHA256 hash"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

def load_metadata():
    """讀取 metadata.json，如果不存在就回傳空 dict"""
    if os.path.exists(META_FILE):
        with open(META_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_metadata(meta):
    """儲存 metadata.json"""
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

def update_metadata(path):
    """更新某個檔案的 metadata"""
    meta = load_metadata()
    h = calc_hash(path)
    ts = datetime.now().isoformat(timespec="seconds")
    meta[path] = {"hash": h, "timestamp": ts}
    save_metadata(meta)
    print(f"已更新 {path} → hash={h[:8]}..., time={ts}")

if __name__ == "__main__":
    # 假設 worker_manual.txt 是知識庫檔案
    file_path = "worker_manual.txt"

    # 如果檔案不存在，先寫一個測試檔
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("公司員工手冊 v1.0\n出勤規範：上班 9-6\n")

    # 更新 metadata
    update_metadata(file_path)

    # 顯示 metadata.json
    print("\n目前的 metadata.json：")
    print(json.dumps(load_metadata(), indent=2, ensure_ascii=False))
