# -*- coding: utf-8 -*-
# ft_prep_from_kb.py (messages 版本)
"""
從 KB（data/kb.jsonl）擷取文本，輸出「使用者自然問句 → 客服回覆」的 fine-tune JSONL。
重點：
- 內建固定 instruction，強化『溫和、專業、簡潔 + 三段式條列』的語氣與格式。
- 每條 KB 產生 1~N 個自然問句；可選擇同時加入「原始陳述 → 回覆」樣本（--also-from-statement）。
- 以 data/ft_cursor.json 記錄已輸出筆數；支援 --force-all / --since。
"""
import os, json, argparse, datetime, sys, re, random
from typing import List
from qa_templates import TEMPLATES_GENERIC, DOMAIN_RULES

DATA_DIR  = "data"
KB_PATH   = os.path.join(DATA_DIR, "kb.jsonl")
META_PATH = os.path.join(DATA_DIR, "kb_meta.json")
CUR_PATH  = os.path.join(DATA_DIR, "ft_cursor.json")

SYSTEM_PROMPT = "請以『溫和、專業、簡潔』的客服口吻回答，並用三段式條列 1–3 點重點。"

# ---------- 基本 I/O ----------
def ensure_exists(path: str, hint: str):
    if not os.path.exists(path):
        print(f"❌ 找不到 {path}（{hint}）", file=sys.stderr)
        sys.exit(2)

def load_lines(path: str) -> List[dict]:
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for l in f:
            s = l.strip()
            if s:
                lines.append(json.loads(s))
    return lines

# ---------- 回覆模板 ----------
def bulletize(text: str, max_items=3) -> List[str]:
    seps = ["；", "。", "，", ";", ".", ","]
    items = [text]
    for sep in seps:
        if len(items) == 1:
            items = [x.strip() for x in items[0].split(sep) if x.strip()]
    cleaned = []
    for it in items[:max_items]:
        it = it.strip().rstrip("；。；，,.;").strip()
        if it:
            cleaned.append(it)
    return cleaned or [text.strip()]

def wrap_as_reply(text: str) -> str:
    pts = bulletize(text, 3)
    pts_fmt = "\n".join([f"{i+1}) {p}" for i, p in enumerate(pts)])
    today = datetime.date.today().isoformat()
    return (
        "您好，感謝您的提問，以下為重點整理：\n\n"
        f"{pts_fmt}\n\n"
        "後續若需要協助，請隨時與我們聯絡。\n"
        f"（內部資料更新日：{today}）"
    )

# ---------- 問句產生 ----------
def pick_domain_questions(text: str) -> List[str]:
    qs = []
    for pat, qlist in DOMAIN_RULES:
        if re.search(pat, text, flags=re.IGNORECASE):
            qs.extend(qlist)
    return qs

def summarize_focus(text: str) -> str:
    s = text.strip()
    s = re.sub(r"[。；；，,.;]\s*$", "", s)
    return s[:20] if len(s) > 20 else s

def gen_questions(text: str, max_n: int = 2) -> List[str]:
    domain_qs = pick_domain_questions(text)
    focus = summarize_focus(text)
    generic_qs = [tpl.format(focus=focus) for tpl in TEMPLATES_GENERIC]

    pool = domain_qs + generic_qs
    dedup, seen = [], set()
    for q in pool:
        q = q.strip("？? ").replace("  ", " ")
        if len(q) < 4:
            continue
        if q not in seen:
            dedup.append(q); seen.add(q)

    random.shuffle(dedup)
    return dedup[:max_n] if dedup else [f"{focus}要怎麼做？"]

# ---------- 游標切片 ----------
def slice_new(kb_all: List[dict], exported: int, since: int = None, force_all: bool = False):
    if force_all:
        return kb_all
    if since is not None:
        return kb_all[max(0, len(kb_all) - since):]
    return kb_all[exported:]

# ---------- 主流程 ----------
def main(args):
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    ensure_exists(KB_PATH, "請先準備 data/kb.jsonl")

    kb = load_lines(KB_PATH)
    total = len(kb)

    meta = {}
    if os.path.exists(META_PATH):
        try:
            meta = json.load(open(META_PATH, encoding="utf-8"))
        except Exception:
            meta = {}

    cursor = {"exported_doc_count": 0}
    if os.path.exists(CUR_PATH):
        try:
            cursor = json.load(open(CUR_PATH, encoding="utf-8"))
        except Exception:
            pass
    start = int(cursor.get("exported_doc_count", 0))

    new_slice = slice_new(kb, start, since=args.since, force_all=args.force_all)
    if not new_slice:
        print(f"✅ 無新增：KB 目前 {total} 筆，已匯出至 {start}。")
        return

    out_cnt = 0
    with open(args.out, "w", encoding="utf-8") as w:
        for ex in new_slice:
            src = (ex.get("text") or "").strip()
            if not src:
                continue
            reply = wrap_as_reply(src)
            questions = gen_questions(src, max_n=args.max_qa_per_doc)
            for q in questions:
                obj = {
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": q},
                        {"role": "assistant", "content": reply}
                    ]
                }
                w.write(json.dumps(obj, ensure_ascii=False) + "\n")
                out_cnt += 1

    # 更新游標
    if not args.force_all and args.since is None:
        with open(CUR_PATH, "w", encoding="utf-8") as c:
            json.dump(
                {"exported_doc_count": total, "kb_version": meta.get("kb_version", 0)},
                c, ensure_ascii=False, indent=2
            )

    picked = len(new_slice)
    print(f"✅ 已輸出 {out_cnt} 筆（{picked} 條文 × 每條最多 {args.max_qa_per_doc} 問句）→ {args.out}")
    print(f"   KB 總筆數 {total}；原游標 {start} → {total}（force_all={args.force_all}, since={args.since}）")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="scenarios/open_ai/train_new.jsonl",
                    help="輸出 JSONL 路徑")
    ap.add_argument("--max-qa-per-doc", type=int, default=2,
                    help="每條 KB 產生問句數上限（預設 2）")
    ap.add_argument("--force-all", action="store_true",
                    help="無視游標輸出整個 KB")
    ap.add_argument("--since", type=int, default=None,
                    help="只輸出最近 N 條（互斥於游標與 --force-all）")
    args = ap.parse_args()
    random.seed(42)  # 讓輸出可重現
    main(args)
