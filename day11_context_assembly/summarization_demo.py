# summarization_demo.py（mT5 版本，含穩定性修正）
# 功能：讀取 Day10 的 reranked.json，對候選文件做「生成式摘要 or 重點擷取」，
#      再把摘要組成 Prompt，供 Day11 的「Summarization 組裝」示範使用。
#
# 重點：
# - PRIMARY_MODEL 改為 mT5（csebuetnlp/mT5_multilingual_XLSum），避開 Pegasus/sentencepiece 易踩坑。
# - 優先載入 safetensors（transformers>=4.44 + torch>=2.6 比較穩）。
# - 針對 T5 家族，自動加 "summarize: " 前綴，提高摘要效果。
# - 長文切塊（token 限制 + overlap），map-reduce 聚合。
# - 短文直接當重點片段，避免小段落也硬摘要而產生怪句。
# - 失敗自動 fallback（FALLBACK_MODEL）。

import os
import sys
import json
import math
import argparse
from typing import List, Dict, Tuple

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")  # 降低 tokenizer 併發警告

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# ---- 路徑與模型設定 ----
DEFAULT_IN_PATH = "reranked.json"

# 以 mT5 多語摘要模型作為主力，較穩定且常見提供 safetensors 權重
PRIMARY_MODEL  = "csebuetnlp/mT5_multilingual_XLSum"
# 後備模型（若主模型載入失敗），同屬 T5 家族，保留一致的前綴行為
FALLBACK_MODEL = "google/mt5-small"


# -------------------------
# 輔助：資料載入
# -------------------------
def load_reranked(path: str, top_n: int = 3) -> Tuple[str, List[str], List[Dict]]:
    if not os.path.exists(path):
        print(f"找不到輸入檔：{path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "reranked" not in data or not data["reranked"]:
        print("reranked.json 缺少 'reranked' 或內容為空")
        sys.exit(1)
    items = data["reranked"][:top_n]            # 前 N 筆（已重排）
    docs  = [it.get("text", "") for it in items]
    query = data.get("query", "")
    return query, docs, items


# -------------------------
# 輔助：裝置選擇
# -------------------------
def pick_device(prefer: str = "auto") -> torch.device:
    if prefer == "cpu":
        return torch.device("cpu")
    if prefer == "cuda" and torch.cuda.is_available():
        return torch.device("cuda")
    if prefer == "mps" and getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    # auto
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


# -------------------------
# 輔助：模型家族判定（T5 系）
# -------------------------
def is_t5_family(model) -> bool:
    cfg = getattr(model, "config", None)
    mt = getattr(cfg, "model_type", "") if cfg else ""
    return "t5" in mt  # t5 / mt5 / flan-t5


# -------------------------
# Token 級切塊（避免輸入過長）
# -------------------------
def split_by_tokens(text: str, tok: AutoTokenizer, max_tokens: int, overlap: int = 100) -> List[str]:
    ids = tok.encode(text, add_special_tokens=True)
    if len(ids) <= max_tokens:
        return [text]
    out, start, n = [], 0, len(ids)
    while start < n:
        end = min(n, start + max_tokens)
        out.append(tok.decode(ids[start:end], skip_special_tokens=True))
        if end == n:
            break
        start = max(0, end - overlap)
    return out


# -------------------------
# 單次摘要（短文）
# -------------------------
@torch.inference_mode()
def summarize_once(
    text: str,
    tok: AutoTokenizer,
    model: AutoModelForSeq2SeqLM,
    device: torch.device,
    min_len: int,
    max_len: int,
    prefix: str = ""
) -> str:
    inp = (prefix + text) if prefix else text
    inputs = tok(inp, return_tensors="pt", truncation=True, max_length=1024).to(device)
    out = model.generate(
        **inputs,
        max_length=max_len,
        min_length=min_len,
        num_beams=4,
        do_sample=False,
        no_repeat_ngram_size=3,
        early_stopping=True,
    )
    return tok.decode(out[0], skip_special_tokens=True)


# -------------------------
# 長文摘要（map-reduce）
# -------------------------
def summarize_long_text(
    text: str,
    tok: AutoTokenizer,
    model: AutoModelForSeq2SeqLM,
    device: torch.device,
    max_inp_tokens: int = 800,
    min_len: int = 20,
    max_len: int = 80,
    prefix: str = ""
) -> str:
    parts = split_by_tokens(text, tok, max_tokens=max_inp_tokens, overlap=128)
    if len(parts) == 1:
        return summarize_once(parts[0], tok, model, device, min_len, max_len, prefix)
    # 先對每個切片做短摘要，再把多個摘要合併成一段，再做一次總結
    partial = [
        summarize_once(p, tok, model, device, max(10, min_len // 2), max_len, prefix)
        for p in parts
    ]
    merged = "。".join([p for p in partial if p.strip()])
    return summarize_once(merged, tok, model, device, min_len, max_len, prefix)


# -------------------------
# Prompt 組裝（教學用簡版）
# -------------------------
def build_prompt(query: str, summaries: List[str]) -> str:
    ctx = "\n".join(summaries)
    return f"""
你是一個樂於助人的助手。
以下提供的是文件的「摘要」或「重點片段」。請僅根據這些內容回答問題。
若找不到答案，請回答「我不知道」。

問題：{query}

文件重點：
{ctx}

請用完整句子作答：
""".strip()


# -------------------------
# 顯示分數格式化
# -------------------------
def fmt_score(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "-"
    try:
        return f"{float(x):.4f}"
    except Exception:
        return str(x)


# -------------------------
# 內部：安全載入（優先 safetensors）
# -------------------------
def _load_model_and_tokenizer(model_id_or_dir: str, local: bool = False):
    kw_tok = dict(use_fast=False)  # T5/mT5 常用 sentencepiece，慢速版較穩
    kw_mod = dict(use_safetensors=True, trust_remote_code=False)
    if local:
        kw_tok.update(local_files_only=True)
        kw_mod.update(local_files_only=True)
    tok = AutoTokenizer.from_pretrained(model_id_or_dir, **kw_tok)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_id_or_dir, **kw_mod)
    return tok, model


# -------------------------
# 主程式
# -------------------------
def main():
    ap = argparse.ArgumentParser(
        description="從 reranked.json 讀取重排結果，做中文 Summarization 上下文組裝（含短文保底與長文切塊）。"
    )
    ap.add_argument("--in", dest="in_path", default=DEFAULT_IN_PATH, help="輸入檔（預設：reranked.json）")
    ap.add_argument("--top-n", type=int, default=3, help="取前 N 筆（預設：3）")
    ap.add_argument("--model", default=PRIMARY_MODEL, help=f"主模型（預設：{PRIMARY_MODEL}）")
    ap.add_argument("--model-dir", default=None, help="本地模型目錄（優先使用本地，無則線上）")
    ap.add_argument("--min-length", type=int, default=20)
    ap.add_argument("--max-length", type=int, default=80)
    ap.add_argument("--max-input-tokens", type=int, default=800)
    ap.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda", "mps"])
    ap.add_argument("--skip-short-chars", type=int, default=60, help="文字長度低於此閾值，直接當重點片段，不做摘要")
    args = ap.parse_args()

    # 讀入資料
    query, docs, items = load_reranked(args.in_path, top_n=args.top_n)

    print("=== 將使用的前 N 篇文件（重排序後）===")
    for i, it in enumerate(items, 1):
        print(f"[{i:02d}] re={fmt_score(it.get('reranker_score'))} | "
              f"ret={fmt_score(it.get('retriever_score'))} | "
              f"idx={it.get('idx')} | {it.get('text','').strip()}")

    # 裝置
    device = pick_device(args.device)
    print(f"\n▶ 使用裝置：{device} | 模型：{args.model}")

    # 版本說明（避免 CVE 問題）
    ver = tuple(int(x) for x in torch.__version__.split("+")[0].split(".")[:2])
    if ver < (2, 6):
        print(f"⚠️ 偵測到 torch=={torch.__version__} < 2.6；將只載入 safetensors 權重（已強制 use_safetensors=True）。")

    # 載入模型（本地優先 → 線上；失敗則 fallback）
    try:
        if args.model_dir:
            tok, model = _load_model_and_tokenizer(args.model_dir, local=True)
        else:
            tok, model = _load_model_and_tokenizer(args.model, local=False)
    except Exception as e:
        print(f"\n⚠️ 載入主模型失敗：{e}\n改用備援模型：{FALLBACK_MODEL}")
        tok, model = _load_model_and_tokenizer(FALLBACK_MODEL, local=False)

    # 模型就緒
    model.to(device)
    model.eval()
    t5_prefix = "summarize: " if is_t5_family(model) else ""  # T5/mT5 家族建議加前綴

    # 逐篇處理：短文→直接收錄；長文→生成式摘要（map-reduce）
    final_pieces: List[str] = []
    print("\n開始處理每篇文件 ...")
    for i, doc in enumerate(docs, 1):
        text = (doc or "").strip()
        if not text:
            print(f"[{i:02d}] 跳過：空文字")
            continue

        if len(text) < args.skip_short_chars:
            piece = text  # 短文直接當重點，避免小段也去「硬摘要」而亂講
            print(f"[{i:02d}] 直接收錄為重點片段（長度 {len(text)}）→ {piece}")
        else:
            piece = summarize_long_text(
                text,
                tok,
                model,
                device,
                max_inp_tokens=args.max_input_tokens,
                min_len=args.min_length,
                max_len=args.max_length,
                prefix=t5_prefix,
            )
            print(f"[{i:02d}] 摘要：{piece}")
        final_pieces.append(piece)

    # 組裝 Prompt
    prompt = build_prompt(query, final_pieces)
    print("\n=== （Summarization/重點擷取）組裝後的提示詞 ===\n")
    print(prompt)


if __name__ == "__main__":
    main()
