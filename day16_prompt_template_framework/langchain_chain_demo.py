# langchain_chain_demo.py
"""
這隻程式示範如何使用 LangChain 建立 Prompt Chain：
1. 讀取 prompts/prompts_v1.yaml 作為 Prompt Registry。
2. 提供兩種用法：
   - 用法 A：直接 QA → (context + question) → 答案
   - 用法 B：先摘要再 QA → (context → 摘要 → 問題 → 答案)
3. 透過 PromptTemplate + LLM + OutputParser 組合成 Chain。
4. 在 main 區塊會 demo VPN 文件的 QA 與 Summary-FAQ 兩種流程。

重點：
- 保留 Jinja 風格模板，程式中會自動轉換成 LangChain 格式。
- 使用 ChatOpenAI 作為 LLM Provider。
- 讓讀者看到「輸入/輸出」資料如何在 Chain 裡傳遞。
"""
import os
import re
import yaml
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda

# --- helpers ---
def normalize_template(t: str) -> str:
    """
    LangChain 的 PromptTemplate 採用 Python 的 format 語法：{var}
    我們保留 Day15 的 Jinja 風格，這裡將 {{ var }} 轉成 {var}。
    """
    if not isinstance(t, str):
        return t
    # 例如: "Hello {{ name }}" -> "Hello {name}"
    t = re.sub(r"\{\{\s*", "{", t)
    t = re.sub(r"\s*\}\}", "}", t)
    return t

# 讀取金鑰
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("沒有找到 OPENAI_API_KEY，請檢查環境變數！")

# 模型（temperature 設低一點，輸出更穩定）
MODEL_NAME = "gpt-4o-mini"
llm = ChatOpenAI(model=MODEL_NAME, api_key=api_key, temperature=0)

# 讀 YAML（Day15 的 Prompt Registry）
YAML_PATH = "prompts/prompts_v1.yaml"
if not os.path.exists(YAML_PATH):
    raise FileNotFoundError(f"找不到 {YAML_PATH}，請確認路徑與工作目錄。")

with open(YAML_PATH, "r", encoding="utf-8") as f:
    yml = yaml.safe_load(f) or {}

# 取出模板字串，並轉成 LangChain 可用格式
try:
    raw_summary_template = yml["prompts"]["summary"]["template"]
    raw_faq_template = yml["prompts"]["faq"]["template"]
except KeyError as e:
    raise KeyError(
        f"YAML 結構不符，缺少 {e}. 期待結構為 prompts.summary.template / prompts.faq.template"
    )

summary_template = normalize_template(raw_summary_template)   # 需要 {context}
faq_template = normalize_template(raw_faq_template)           # 需要 {context}、{question}

# Step 1️⃣: 摘要 Prompt（吃 {context}）
summary_prompt = PromptTemplate(
    input_variables=["context"],
    template=summary_template
)
# dict(context=...) → Prompt → LLM → str
summary_chain = summary_prompt | llm | StrOutputParser()

# Step 2️⃣: FAQ Prompt（吃 {context} 與 {question}）
faq_prompt = PromptTemplate(
    input_variables=["context", "question"],
    template=faq_template
)

# --- 用法 A：直接 QA（context + question → faq） ---
# [IN]  {"text": <原始內容>, "question": <問題>}
# [OUT] str（答案）
qa_chain = (
    {
        # 將原始輸入映射到 Prompt 需要的鍵
        "context": RunnableLambda(lambda x: x["text"]),
        "question": RunnableLambda(lambda x: x["question"]),
    }
    | faq_prompt          # dict → Prompt 字串
    | llm                 # Prompt → 模型輸出
    | StrOutputParser()   # → 純文字
)

# --- 用法 B：先摘要再 FAQ（summary → faq） ---
# Step 0️⃣: 定義一個「自動問題產生器」
# 在這裡我們固定輸出一段文字：「請依據以上摘要產生三個常見問題並回答，條列式。」
# 實際應用中，你也可以改成根據情境動態產生不同問題。
# [IN]  {"text": <原始內容>}
# [OUT] str（條列 FAQ）
auto_question = RunnableLambda(
    lambda _: "請依據以上摘要產生三個常見問題並回答，條列式。"
)
summary_to_faq_chain = (
    {
        # Step 1: 從輸入資料結構中取出 text，包裝成 {context}
        # 並先丟給 summary_chain，產生「文件摘要」
        "context": RunnableLambda(lambda x: {"context": x["text"]}) | summary_chain,
        "question": auto_question, # Step 2: 生成問題（固定輸出三個常見問題的要求）
    }
    | faq_prompt            # Step 3: 把 {context, question} 套用到 faq_prompt，組裝完整的 Prompt
    | llm                   # Step 4: 把組裝好的 Prompt 丟給 LLM，產生回答
    | StrOutputParser()     # Step 5: 解析 LLM 輸出，只留下純文字（去掉多餘 metadata）
)

if __name__ == "__main__":
    doc = "VPN 設定文件：步驟 1 安裝軟體，步驟 2 設定帳號，步驟 3 連線。"

    print("=== 用法 A：直接 QA（context + question → faq） ===")
    out_qa = qa_chain.invoke({"text": doc, "question": "如何設定公司 VPN？"})
    print(out_qa)

    print("\n=== 用法 B：先摘要再 FAQ（summary → faq） ===")
    out_summary_faq = summary_to_faq_chain.invoke({"text": doc})
    print(out_summary_faq)
