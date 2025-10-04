# -*- coding: utf-8 -*-
"""
Cross-Provider LLM-as-a-judge Demo (OpenAI + Gemini)
- 同時呼叫 OpenAI 與 Gemini 做「是否忠於文件」的審核
- 印出兩者原始輸出 + 標準化後判斷（OK/Hallucination）
- 給出 AND / OR / CONSENSUS 三種決策策略結果
- .env 自動載入 OPENAI_API_KEY / GOOGLE_API_KEY
- --strict true：缺金鑰/套件/API 失敗就報錯，不回退
"""

import os
import argparse
from typing import List, Tuple, Dict

# 讀 .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

PROMPT_TMPL = """你是一個審核員，請判斷以下回答是否忠於文件。
如果忠於文件，回覆：OK
如果不是，回覆：Hallucination

文件片段：
{context}

模型回答：
{answer}
"""

def _normalize(label: str) -> str:
    """將任意輸出歸一成 OK / Hallucination 兩類。"""
    s = (label or "").strip().upper()
    return "OK" if s.startswith("OK") else "Hallucination"

def judge_openai(answer: str, docs: List[str], model: str = "gpt-4o-mini",
                 verbose: bool = True, strict: bool = False) -> Tuple[str, str]:
    """
    回傳 (raw, norm)；norm ∈ {"OK","Hallucination"}
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if verbose:
        print(f"[OpenAI] key_present={bool(api_key)} model={model}")
    if not api_key:
        msg = "未偵測到 OPENAI_API_KEY"
        if strict: raise RuntimeError(msg)
        raw = "NO_API_KEY"
        return raw, _normalize(raw)

    try:
        from openai import OpenAI
    except Exception as e:
        if strict: raise
        if verbose: print(f"（注意）openai 套件不可用：{e}")
        raw = "OPENAI_SDK_MISSING"
        return raw, _normalize(raw)

    client = OpenAI(api_key=api_key)
    prompt = PROMPT_TMPL.format(context=docs[0] if docs else "", answer=answer)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        raw = (resp.choices[0].message.content or "").strip()
        norm = _normalize(raw)
        if verbose:
            print(f"[OpenAI raw] {raw}")
            print(f"[OpenAI judge] {norm}")
        return raw, norm
    except Exception as e:
        if strict: raise
        if verbose: print(f"呼叫 OpenAI 失敗：{e}")
        raw = "OPENAI_CALL_FAILED"
        return raw, _normalize(raw)

def judge_gemini(answer: str, docs: List[str], model: str = "gemini-1.5-flash",
                 verbose: bool = True, strict: bool = False) -> Tuple[str, str]:
    """
    回傳 (raw, norm)；norm ∈ {"OK","Hallucination"}
    """
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if verbose:
        print(f"[Gemini] key_present={bool(api_key)} model={model}")
    if not api_key:
        msg = "未偵測到 GOOGLE_API_KEY"
        if strict: raise RuntimeError(msg)
        raw = "NO_API_KEY"
        return raw, _normalize(raw)

    try:
        import google.generativeai as genai
    except Exception as e:
        if strict: raise
        if verbose: print(f"（注意）google-generativeai 套件不可用：{e}")
        raw = "GEMINI_SDK_MISSING"
        return raw, _normalize(raw)

    genai.configure(api_key=api_key)
    prompt = PROMPT_TMPL.format(context=docs[0] if docs else "", answer=answer)

    try:
        print(">>> USING GEMINI <<<")  # 明確標示真的在呼叫 Gemini
        model_obj = genai.GenerativeModel(model)
        resp = model_obj.generate_content(
            prompt,
            safety_settings=[],                    # 視需要加安全設定
            generation_config={"temperature": 0.0}
        )
        raw = (resp.text or "").strip()
        norm = _normalize(raw)
        if verbose:
            print(f"[Gemini raw] {raw}")
            print(f"[Gemini judge] {norm}")
        return raw, norm
    except Exception as e:
        if strict: raise
        if verbose: print(f"呼叫 Gemini 失敗：{e}")
        raw = "GEMINI_CALL_FAILED"
        return raw, _normalize(raw)

def ensemble_decisions(openai_norm: str, gemini_norm: str) -> Dict[str, str]:
    """
    回傳三種策略的最終判斷：
    - AND：兩者都 OK 才 OK
    - OR：任一為 OK 即 OK
    - CONSENSUS：兩者一致才採用；不一致 → "REVIEW"
    """
    and_ok = "OK" if (openai_norm == "OK" and gemini_norm == "OK") else "Hallucination"
    or_ok  = "OK" if (openai_norm == "OK" or  gemini_norm == "OK") else "Hallucination"
    consensus = openai_norm if openai_norm == gemini_norm else "REVIEW"
    return {"AND": and_ok, "OR": or_ok, "CONSENSUS": consensus}

def run_one_case(label: str, docs: List[str], answer: str,
                 openai_model: str, gemini_model: str,
                 verbose: bool, strict: bool):
    print("=" * 80)
    print(label)
    print("- Context:", docs[0] if docs else "(empty)")
    print("- Answer :", answer)

    o_raw, o_norm = judge_openai(answer, docs, model=openai_model, verbose=verbose, strict=strict)
    g_raw, g_norm = judge_gemini(answer, docs, model=gemini_model, verbose=verbose, strict=strict)

    print("\n[Summary]")
    print(f"OpenAI  → {o_norm}")
    print(f"Gemini  → {g_norm}")

    ens = ensemble_decisions(o_norm, g_norm)
    print("\n[Ensemble]")
    print(f"AND       : {ens['AND']}   (兩者都 OK 才通過)")
    print(f"OR        : {ens['OR']}    (任一 OK 即通過)")
    print(f"CONSENSUS : {ens['CONSENSUS']}   (不一致 → REVIEW)")

def main():
    parser = argparse.ArgumentParser(description="Cross-Provider LLM-as-a-judge Demo（OpenAI + Gemini）")
    parser.add_argument("--openai-model", default="gpt-4o-mini")
    parser.add_argument("--gemini-model", default="gemini-1.5-flash")
    parser.add_argument("--verbose", type=lambda x: x.lower() != "false", default=True)
    parser.add_argument("--strict", type=lambda x: x.lower() == "true", default=False)

    # demo 模式（跑正反兩個示例），或自訂輸入
    parser.add_argument("--mode", choices=["demo", "custom"], default="demo")
    parser.add_argument("--context", default="公司 VPN 設定文件：步驟 1 安裝軟體，步驟 2 設定帳號，步驟 3 連線。")
    parser.add_argument("--answer", default="")
    args = parser.parse_args()

    docs = [args.context] if args.context else []

    if args.mode == "demo":
        grounded_answer = (
            "依文件步驟：先安裝 VPN 軟體，以公司帳號登入後再嘗試連線。"
            "若需要詳細設定，請參考 IT 提供的安裝指南頁面。"
        )
        hallucinated_answer = (
            "請編輯 /etc/vpn/config，把伺服器設為 10.0.0.5，"
            "存檔後執行 vpnctl --force 重啟即可。"
        )
        run_one_case("示例 A（合理對照）", docs, grounded_answer,
                     args.openai_model, args.gemini_model, args.verbose, args.strict)
        run_one_case("示例 B（幻覺範例）", docs, hallucinated_answer,
                     args.openai_model, args.gemini_model, args.verbose, args.strict)
    else:
        if not args.answer:
            raise SystemExit("custom 模式請提供 --answer")
        run_one_case("自訂案例", docs, args.answer,
                     args.openai_model, args.gemini_model, args.verbose, args.strict)

if __name__ == "__main__":
    main()
