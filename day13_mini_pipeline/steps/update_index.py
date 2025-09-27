# steps/update_index.py
from __future__ import annotations
import json, os
from typing import List, Dict, Any

def ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)

def write_index(index_path: str, records: List[Dict[str, Any]]) -> None:
    ensure_dir(index_path)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({"count": len(records), "items": records}, f, ensure_ascii=False, indent=2)
