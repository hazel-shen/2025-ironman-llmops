from __future__ import annotations
from pathlib import Path
from typing import List

# 專案根與資料路徑
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_FILE = DATA_DIR / "worker_manual.txt"
INDEX_FILE = DATA_DIR / "vector_index.json"

def clean_text(text: str) -> str:
    """最小清洗：去頭尾空白、過濾空行。"""
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())

def chunk_text(text: str, max_chars: int = 300) -> List[str]:
    """最小切片：依字數粗略切段。"""
    buf, chunks = "", []
    for line in text.splitlines():
        if len(buf) + len(line) + 1 > max_chars:
            if buf:
                chunks.append(buf)
            buf = line
        else:
            buf = f"{buf}\n{line}" if buf else line
    if buf:
        chunks.append(buf)
    return chunks
