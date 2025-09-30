# langchain_chain_router_demo.py
"""
示範 Router Chain（條件分流）：
1. 讀取 prompts/prompts_v1.yaml（pricing 模板可選）
2. 建立三條子流程：
   - summary_chain：文件摘要
   - faq_chain：FAQ 問答
   - pricing_chain：價格相關回答（若 YAML 無對應模板，使用內建預設）
3. Router 規則：
   - 問題含「價格/費用/price/pricing」→ pricing_chain
   - 問題非價格 → faq_chain
   - 沒有 question → summary_chain
"""

import os
import re
import yaml
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnableBranch

# --- helpers ---
def normalize_template(t: str) -> str:
    """將 Jinja 風格 {{ var }} 轉成 LangChain {var}。"""
    if not isinstance(t, str):
        return t
    t = re.sub(r"\{\{\s*", "{", t)
    t = re.sub(r"\s*\}\}", "}", t)
    return t

def has_pricing_keyword(q: str) -> bool:
    if not q:
        return False
    kw = ["價格", "費用", "價錢", "收費", "多少錢", "price", "pricing", "cost", "costs"]
    ql = q.lower()
    return any(k in q or k in ql for k in kw)

# 讀取金鑰
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("沒有找到 OPENAI_API_KEY，請檢查環境變數！")

# LLM
MODEL_NAME = "gpt-4o-mini"
llm = ChatOpenAI(model=MODEL_NAME, api_key=api_key, temperature=0)

# 讀 YAML（Prompt Registry）
YAML_PATH = "prompts/prompts_v1.yaml"
if not os.path.exists(YAML_PATH):
    raise FileNotFoundError(f"找不到 {YAML_PATH}，請確認路徑與工作目錄。")

with open(YAML_PATH, "r", encoding="utf-8") as f:
    yml = yaml.safe_load(f) or {}

prompts = yml.get("prompts") or {}

# 必要模板：summary / faq
raw_summary_template = (prompts.get("summary") or {}).get("template")
raw_faq_template = (prompts.get("faq") or {}).get("template")
if not raw_summary_template or not raw_faq_template:
    raise KeyError(
        "YAML 結構不符，缺少 prompts.summary.template 或 prompts.faq.template"
    )

# 可選模板：pricing（不存在就用預設）
raw_pricing_template = (prompts.get("pricing") or {}).get("template")

DEFAULT_PRICING_TEMPLATE = """你是客服助理。請根據以下內容回答與價格/費用相關的問題；若文件沒有明確價格，請說明查詢方式或給出估算因子。
文件內容：
{context}

使用者問題：
{question}

請用條列式，並在最後加入「（若需最新價格，請以官網或業務回覆為準）」。
"""

summary_template = normalize_template(raw_summary_template)
faq_template = normalize_template(raw_faq_template)
pricing_template = normalize_template(raw_pricing_template) if raw_pricing_template else DEFAULT_PRICING_TEMPLATE

# === 建立三條子流程 ===
# 1) Summary
summary_prompt = PromptTemplate(input_variables=["context"], template=summary_template)
summary_chain = summary_prompt | llm | StrOutputParser()

# 2) FAQ
faq_prompt = PromptTemplate(input_variables=["context", "question"], template=faq_template)
faq_chain = (
    {
        "context": RunnableLambda(lambda x: x["text"]),
        "question": RunnableLambda(lambda x: x.get("question", "")),
    }
    | faq_prompt
    | llm
    | StrOutputParser()
)

# 3) Pricing
pricing_prompt = PromptTemplate(input_variables=["context", "question"], template=pricing_template)
pricing_chain = (
    {
        "context": RunnableLambda(lambda x: x["text"]),
        "question": RunnableLambda(lambda x: x.get("question", "")),
    }
    | pricing_prompt
    | llm
    | StrOutputParser()
)

# === Router（條件分流） ===
# 讓「只有文件」的輸入先轉成 summary_chain 需要的鍵
summary_entry = RunnableLambda(lambda x: {"context": x["text"]}) | summary_chain

# [IN]  {"text": <長文>, "question": Optional[str]}
# [OUT] str
router = RunnableBranch(
    (lambda x: "question" not in x or not x["question"], summary_entry),     # 無 question → Summary（先映射成 context）
    (lambda x: has_pricing_keyword(x.get("question", "")), pricing_chain),   # 有價格關鍵詞 → Pricing
    faq_chain,  # 其他 → FAQ
)

if __name__ == "__main__":
    doc = (
        "產品說明：標準版提供核心功能；進階版包含自動化報表。\n"
        "標準版定價通常以用量區間為準，企業合約另議；部署可選雲端或自建。"
    )

    print("=== Case 1：只有文件（無 question）→ Summary ===")
    out1 = router.invoke({"text": doc})
    print(out1)

    print("\n=== Case 2：價格相關問題 → Pricing ===")
    out2 = router.invoke({"text": doc, "question": "進階版多少錢？是否有企業方案的收費？"})
    print(out2)

    print("\n=== Case 3：一般問題 → FAQ ===")
    out3 = router.invoke({"text": doc, "question": "標準版與進階版差在哪？"})
    print(out3)
