# guidance_faq_json_robust.py
import os, re, json
from dotenv import load_dotenv
import guidance
from guidance import models
from openai import OpenAI

# ---------- 基本設定 ----------
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("沒有找到 OPENAI_API_KEY，請檢查 .env！")

MODEL_NAME = "gpt-4o-mini"
llm = models.OpenAI(model=MODEL_NAME, api_key=api_key)
oai = OpenAI(api_key=api_key)

# ---------- Guidance 程式（要求只輸出 JSON） ----------
@guidance
def faq_json_program(lm, draft):
    lm += f"""
你會收到一段 FAQ 草稿，請轉成 JSON 陣列，每個元素必須包含 "q" 與 "a" 欄位。
嚴格要求：只輸出合法 JSON，不要前後多任何文字、說明或標記。

FAQ 草稿：
{draft}

輸出：
{{{{gen 'json' temperature=0 max_tokens=800}}}}
"""
    return lm

# ---------- 工具：從 Guidance 取出純文字 ----------
GUIDANCE_TAG_RE = re.compile(r"\{\{G\|.*?\|G\}\}", re.S)
JSON_SNIPPET_RE = re.compile(r"(\{.*\}|\[.*\])", re.S)

def _materialize_to_text(prog) -> str:
    """把 guidance 回傳物件執行並盡力取回文字（兼容不同版本）"""
    res = prog
    for _ in range(3):
        if not callable(res):
            break
        for attempt in (lambda r: r(), lambda r: r(model=llm), lambda r: r(llm)):
            try:
                res = attempt(res)
                break
            except TypeError:
                continue
        else:
            break
    # 優先用 res.text，失敗就 str(res)
    txt = getattr(res, "text", None)
    if isinstance(txt, str) and txt.strip():
        return txt
    return str(res)

def _clean_and_extract_json(text: str):
    """清掉 Guidance 內部標記並嘗試擷取 JSON 片段"""
    if not isinstance(text, str):
        return None
    text = GUIDANCE_TAG_RE.sub("", text).strip()
    # 直接嘗試 parse
    for candidate in (text,):
        try:
            return json.loads(candidate)
        except Exception:
            pass
    # 從長文本內擷取第一段看似 JSON 的片段
    m = JSON_SNIPPET_RE.search(text)
    if m:
        snippet = m.group(1).strip()
        try:
            return json.loads(snippet)
        except Exception:
            return {"raw_output": snippet}  # 至少回給你片段
    return {"raw_output": text}  # 最後退路

# ---------- Fallback：OpenAI 官方 SDK ----------
def _fallback_openai(draft: str):
    sys = "你是一個嚴格的格式器。只輸出 JSON，不要多餘文字。"
    user = f"""將下面 FAQ 草稿轉成 JSON 陣列，元素包含 "q" 與 "a"。
嚴格只輸出合法 JSON。

FAQ 草稿：
{draft}
"""
    resp = oai.chat.completions.create(
        model=MODEL_NAME,
        temperature=0,
        messages=[{"role":"system","content":sys},{"role":"user","content":user}],
    )
    txt = resp.choices[0].message.content or ""
    # 移除可能的 code block 標記
    txt = txt.strip()
    txt = re.sub(r"^```json\s*|\s*```$", "", txt)
    return json.loads(txt)

# ---------- 封裝：先 Guidance，失敗就 SDK ----------
def run_faq_to_json(draft: str):
    try:
        prog = faq_json_program(model=llm, draft=draft)
        txt = _materialize_to_text(prog)
        data = _clean_and_extract_json(txt)
        # 若只有 raw_output 且不是 JSON，啟動 fallback
        if isinstance(data, dict) and "raw_output" in data:
            raise ValueError("Guidance 輸出非 JSON，啟用 fallback")
        return data
    except Exception:
        # 最後保障：用官方 SDK 生成
        return _fallback_openai(draft)

# ---------- 測試 ----------
if __name__ == "__main__":
    draft = """
Q: 公司 VPN 怎麼設定？
A: 請先安裝軟體，接著輸入帳號密碼，最後按下連線。
"""
    result = run_faq_to_json(draft)
    print("=== FAQ JSON ===")
    print(result)
