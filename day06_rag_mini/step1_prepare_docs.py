# step1_prepare_docs.py
import json
from pathlib import Path

DOCS = [
    "請假流程：需要先主管簽核，然後到 HR 系統提交。",
    "加班申請：需事先提出，加班工時可折換補休。",
    "報銷規則：需要提供發票，金額超過 1000 需經理簽核。"
]

def main():
    out = Path("data")
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "docs.json", "w", encoding="utf-8") as f:
        json.dump(DOCS, f, ensure_ascii=False, indent=2)
    print("✅ 已寫入 data/docs.json")

if __name__ == "__main__":
    main()
