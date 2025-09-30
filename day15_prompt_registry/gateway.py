# gateway.py
from pathlib import Path
from fastapi import FastAPI, Header
from pydantic import BaseModel
from typing import Optional
import logging
import os
from dotenv import load_dotenv
from openai import OpenAI

from registry.registry import PromptRegistry

# 載入 .env
load_dotenv()

# 檢查 API Key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("沒有找到 OPENAI_API_KEY，請檢查環境變數！")

# 初始化 OpenAI client
client = OpenAI(api_key=api_key)

# FastAPI
app = FastAPI(title="Prompt Registry Gateway")
log = logging.getLogger("gateway")
logging.basicConfig(level=logging.INFO)

# 載入 prompts
# registry/ 下會有多個 prompts_vX.yaml
# PromptRegistry 負責統一載入、管理與渲染這些 Prompt 模板
REG = PromptRegistry(str(Path(__file__).resolve().parent / "prompts"))

# Pydantic BaseModel 負責驗證請求參數格式
class AskBody(BaseModel):
    question: str                 # 使用者的問題
    context: str                  # 文件上下文 (可選：檢索回來的片段)
    prompt_name: str = "faq"      # 要使用的 Prompt 名稱 (預設 faq)
    prompt_version: str = "v2"    # Prompt 版本 (預設 v2)
    model: str = "gpt-4o-mini"    # 使用的 LLM 模型 (預設 gpt-4o-mini)

@app.get("/versions")
def versions():
    """
    列出目前可用的 Prompt 版本
    例如: ["v1", "v2"]
    """
    return {"versions": REG.list_versions()}

@app.get("/prompts/{version}")
def prompts(version: str):
    """
    查看某個版本底下有哪些 Prompt
    例如: GET /prompts/v2
    回傳 ["faq", "summary"]
    """
    return {"version": version, "prompts": REG.list_prompts(version)}

@app.post("/ask")
def ask(body: AskBody, x_prompt_version: Optional[str] = Header(None)):
    """
    主功能：接收使用者問題，透過 Prompt Registry 渲染後送去 LLM
    """
    # 如果 header 裡有指定版本，會覆蓋 body 的設定
    version = x_prompt_version or body.prompt_version
    pid = f"{body.prompt_name}:{version}"

    # 1. 渲染 Prompt
    # 從 Registry 拿到模板，替換 {{context}} 與 {{question}}
    prompt = REG.render(
        body.prompt_name, version,
        context=body.context, question=body.question
    )

    # 2. 呼叫 OpenAI API
    resp = client.chat.completions.create(
        model=body.model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    resp_text = resp.choices[0].message.content

    # 3. 記錄日誌
    # 方便之後 Debug：知道用的是哪個 Prompt + 哪個模型
    log.info("ASK prompt_id=%s model=%s q=%r", pid, body.model, body.question)

    # 4. 回傳結果
    return {
        "answer": resp_text,   # LLM 的回覆
        "prompt_id": pid,      # 使用的 Prompt 名稱 + 版本
        "model": body.model    # 呼叫的模型
    }