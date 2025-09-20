# utils_openai.py
# 小工具模組，把 OpenAI 的常用動作（產生 embedding、呼叫聊天模式）
# 讓 step2 和 step3 的程式可以呼叫

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
_client = None

def get_openai_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"

def embed(text: str):
    client = get_openai_client()
    resp = client.embeddings.create(model=EMBED_MODEL, input=text)
    return resp.data[0].embedding

def chat_answer(system_prompt: str, user_prompt: str):
    client = get_openai_client()
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )
    return resp.choices[0].message.content
