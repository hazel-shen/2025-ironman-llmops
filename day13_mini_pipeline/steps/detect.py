# steps/detect.py
from __future__ import annotations
import hashlib, os, time
from dataclasses import dataclass

@dataclass
class DetectResult:
    changed: bool
    new_hash: str
    old_hash: str | None
    mtime: float

def file_md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def detect_change(src_path: str, meta_hash_path: str) -> DetectResult:
    if not os.path.exists(src_path):
        raise FileNotFoundError(f"Source not found: {src_path}")

    new_hash = file_md5(src_path)
    old_hash = None
    if os.path.exists(meta_hash_path):
        with open(meta_hash_path, "r", encoding="utf-8") as f:
            old_hash = f.read().strip()

    changed = (old_hash != new_hash)
    mtime = os.path.getmtime(src_path)
    return DetectResult(changed=changed, new_hash=new_hash, old_hash=old_hash, mtime=mtime)

def save_hash(meta_hash_path: str, h: str) -> None:
    os.makedirs(os.path.dirname(meta_hash_path), exist_ok=True)
    with open(meta_hash_path, "w", encoding="utf-8") as f:
        f.write(h)
