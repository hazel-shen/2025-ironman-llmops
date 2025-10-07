# -*- coding: utf-8 -*-
"""
建立或查詢 OpenAI Fine-tuning 工作
需求：
  - 環境變數 OPENAI_API_KEY
用法：
  建立＋等待完成：
    python scripts/openai_finetune.py run --model gpt-4o-mini-2024-07-18 --train_jsonl scenarios/open_ai/train_new.jsonl
  只建立（不等待）：
    python scripts/openai_finetune.py run --model gpt-4o-mini-2024-07-18 --train_jsonl ... --no-wait
  查狀態：
    python scripts/openai_finetune.py status --job ftjob_xxx
"""
import argparse, json, os, time, sys
from pathlib import Path
from openai import OpenAI

def ensure_key():
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ 缺少 OPENAI_API_KEY", file=sys.stderr)
        sys.exit(2)

def run_job(model: str, train_jsonl: str, suffix: str = None, wait: bool = True, poll: int = 10):
    
    # 基本檢查：檔案存在且不是空檔
    if not os.path.exists(train_jsonl):
        print(f"❌ 找不到訓練檔：{train_jsonl}", file=sys.stderr)
        print("   提示：先執行 make ft-export-all 或 make ft-export-last N=10", file=sys.stderr)
        sys.exit(2)
    if os.path.getsize(train_jsonl) == 0:
        print(f"❌ 訓練檔為空：{train_jsonl}", file=sys.stderr)
        print("   提示：執行 make ft-export-all 或 make ft-export-last N=10 產生內容", file=sys.stderr)
        sys.exit(2)

    ensure_key()
    client = OpenAI()

    # 1) 上傳檔案
    f = client.files.create(file=Path(train_jsonl), purpose="fine-tune")

    # 2) 建立工作
    job = client.fine_tuning.jobs.create(model=model, training_file=f.id, suffix=suffix)
    print(json.dumps({"job_id": job.id, "status": job.status, "model": model, "training_file": f.id},
                     ensure_ascii=False, indent=2))

    if not wait:
        return

    # 3) 輪詢直到完成或失敗
    term = {"succeeded", "failed", "cancelled"}
    while True:
        j = client.fine_tuning.jobs.retrieve(job.id)
        if j.status in term:
            # 成功會帶回 fine_tuned_model
            out = {"job_id": j.id, "status": j.status, "fine_tuned_model": getattr(j, "fine_tuned_model", None)}
            print(json.dumps(out, ensure_ascii=False, indent=2))
            break
        time.sleep(poll)

def show_status(job_id: str):
    ensure_key()
    client = OpenAI()
    j = client.fine_tuning.jobs.retrieve(job_id)
    print(json.dumps({
        "job_id": j.id,
        "status": j.status,
        "fine_tuned_model": getattr(j, "fine_tuned_model", None)
    }, ensure_ascii=False, indent=2))

def main():
    ap = argparse.ArgumentParser(prog="openai_finetune")
    sub = ap.add_subparsers(dest="cmd", required=True)

    rp = sub.add_parser("run", help="建立 fine-tune 工作")
    rp.add_argument("--model", required=True, help="基底模型（例如 gpt-4o-mini-2024-07-18）")
    rp.add_argument("--train_jsonl", required=True)
    rp.add_argument("--suffix", default=None)
    rp.add_argument("--no-wait", action="store_true", help="只建立，不等待完成")
    rp.add_argument("--poll", type=int, default=10, help="輪詢秒數")
    rp.set_defaults(func=lambda a: run_job(a.model, a.train_jsonl, a.suffix, not a.no_wait, a.poll))

    sp = sub.add_parser("status", help="查詢工作狀態")
    sp.add_argument("--job", required=True)
    sp.set_defaults(func=lambda a: show_status(a.job))

    args = ap.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
