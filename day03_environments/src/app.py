from fastapi import FastAPI
from openai import OpenAI
from dotenv import load_dotenv
import os

# 載入 .env
load_dotenv()

# 讀取金鑰
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("❌ 找不到 OPENAI_API_KEY，請確認 .env 或環境變數設定")

app = FastAPI()
client = OpenAI(api_key=api_key)

@app.get("/")
def health():
    return {"ok": True}

# 正式情境我們會用 POST & JSON Body 來處理需要編碼的字串
@app.get("/ask")
def ask(q: str):
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": q}]
    )
    return {"question": q, "answer": resp.choices[0].message.content}