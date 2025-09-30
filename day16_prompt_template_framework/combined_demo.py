# combined_demo.py
import os, re, json, yaml
from dotenv import load_dotenv

# LangChain
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda

# Guidance + OpenAI SDK (fallback)
import guidance
from guidance import models
from openai import OpenAI

# =========================
# 基本設定
# =========================
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("沒有找到 OPENAI_API_KEY，請檢查 .env！")

MODEL_NAME = "gpt-4o-mini"  # 直接指定同一個模型名稱
oai = OpenAI(api_key=API_KEY)

# LangChain LLM
lc_llm = ChatOpenAI(model=MODEL_NAME, api_key=API_KEY, temperature=0)

# Guidance LLM
gd_llm = models.OpenAI(model=MODEL_NAME, api_key=API_KEY)

# =========================
# 載入 Day15 的 Prompt Registry（Jinja 風格 {{ }}）
# =========================
YAML_PATH = "prompts/prompts_v1.yaml"
if not os.path.exists(YAML_PATH):
    raise FileNotFoundError(f"找不到 {YAML_PATH}，請確認路徑與工作目錄。")

with open(YAML_PATH, "r", encoding="utf-8") as f:
    yml = yaml.safe_load(f) or {}

try:
    SUMMARY_TPL_JINJA = yml["prompts"]["summary"]["template"]   # 需要 {{ context }}
    FAQ_TPL_JINJA = yml["prompts"]["faq"]["template"]           # 需要 {{ context }} 與 {{ question }}
except KeyError as e:
    raise KeyError(
        f"prompts_v1.yaml 結構不符，缺少 {e}；期待 prompts.summary.template / prompts.faq.template"
    )

# =========================
# 將 Jinja 風格轉成 LangChain 風格（只在 LangChain 端使用）
# =========================
import re
def normalize_template(t: str) -> str:
    """
    LangChain 的 PromptTemplate 用 Python format 語法 {var}；
    但 Day15 Registry 用 Jinja 風格 {{ var }}，不轉換會導致變數無法替換，
    模型看到的仍是「{{ var }}」原文，因此需要將 {{ var }} → {var}。
    """
    if not isinstance(t, str):
        return t
    t = re.sub(r"\{\{\s*", "{", t)
    t = re.sub(r"\s*\}\}", "}", t)
    return t

SUMMARY_TPL_LC = normalize_template(SUMMARY_TPL_JINJA)  # {context}
FAQ_TPL_LC = normalize_template(FAQ_TPL_JINJA)          # {context} / {question}

# =========================
# LangChain：摘要 → FAQ 草稿（文字）
# =========================
# Step 1: 摘要
summary_prompt = PromptTemplate(
    input_variables=["context"],
    template=SUMMARY_TPL_LC
)
summary_chain = summary_prompt | lc_llm | StrOutputParser()

# Step 2: FAQ（把摘要當成 context，question 自動給指示語）
faq_prompt = PromptTemplate(
    input_variables=["context", "question"],
    template=FAQ_TPL_LC
)

auto_question = RunnableLambda(
    lambda _: "請依據以上摘要產生三個常見問題並回答，條列式。"
)

# Workflow：text -> summary -> faq_draft (string)
lc_chain = (
    {
        "context": RunnableLambda(lambda x: {"context": x["text"]}) | summary_chain,
        "question": auto_question,
    }
    | faq_prompt
    | lc_llm
    | StrOutputParser()
)

# =========================
# Guidance：把 FAQ 草稿 → 強制 JSON
# =========================
GUIDANCE_TAG_RE = re.compile(r"\{\{G\|.*?\|G\}\}", re.S)
JSON_SNIPPET_RE = re.compile(r"(\{.*\}|\[.*\])", re.S)

@guidance
def faq_json_program(lm, draft):
    lm += f"""
你會收到一段 FAQ 草稿，請轉成 JSON 陣列，每個元素必須包含 "q" 與 "a" 欄位。
嚴格要求：只輸出合法 JSON，不要前後多任何文字、說明或標記。

FAQ 草稿：
{draft}

輸出：
{{{{gen 'json' temperature=0 max_tokens=1200}}}}
"""
    return lm

def _materialize_to_text(prog) -> str:
    """把 guidance 回傳物件執行到底並取文字（相容不同版本）。"""
    res = prog
    for _ in range(3):
        if not callable(res):
            break
        for attempt in (lambda r: r(), lambda r: r(model=gd_llm), lambda r: r(gd_llm)):
            try:
                res = attempt(res)
                break
            except TypeError:
                continue
        else:
            break
    txt = getattr(res, "text", None)
    if isinstance(txt, str) and txt.strip():
        return txt
    return str(res)

def _clean_and_extract_json(text: str):
    """清掉 Guidance 內部標記並嘗試擷取/解析 JSON。"""
    if not isinstance(text, str):
        return {"raw_output": text}
    text = GUIDANCE_TAG_RE.sub("", text).strip()
    # 先直接嘗試 parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # 從長文本內擷取第一個像 JSON 的片段
    m = JSON_SNIPPET_RE.search(text)
    if m:
        snippet = m.group(1).strip()
        try:
            return json.loads(snippet)
        except Exception:
            return {"raw_output": snippet}
    return {"raw_output": text}

def _fallback_openai_json(draft: str):
    """保險機制：用 OpenAI 官方 SDK 產生 JSON。"""
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
    txt = (resp.choices[0].message.content or "").strip()
    # 去掉可能的 ```json 包裹
    txt = re.sub(r"^```json\s*|\s*```$", "", txt)
    return json.loads(txt)

def guidance_to_json(draft: str):
    """Guidance 轉 JSON；必要時 fallback OpenAI SDK。"""
    prog = faq_json_program(model=gd_llm, draft=draft)
    txt = _materialize_to_text(prog)
    data = _clean_and_extract_json(txt)
    if isinstance(data, dict) and "raw_output" in data:
        # Guidance 版本不穩 → 啟用 fallback
        data = _fallback_openai_json(draft)
    return data

# =========================
# 主流程
# =========================
if __name__ == "__main__":
    # 測試文件
    doc = "VPN 設定文件：步驟 1 安裝軟體，步驟 2 設定帳號，步驟 3 連線。"

    # (1) LangChain：產生 FAQ 草稿（文字）
    faq_draft = lc_chain.invoke({"text": doc})
    print("=== LangChain → FAQ 草稿（文字） ===")
    print(faq_draft)

    # (2) Guidance：把草稿轉成 JSON
    faq_json = guidance_to_json(faq_draft)
    print("\n=== Guidance → FAQ JSON ===")
    print(faq_json)
