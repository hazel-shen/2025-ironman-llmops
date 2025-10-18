# demo_different_prompt.py
import os
from openai import OpenAI
from dotenv import load_dotenv

# 載入 .env 檔
load_dotenv()

# 從環境變數讀取
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI()

def ask(prompt, question):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": question}
        ]
    )
    return response.choices[0].message.content

# Prompt A：客服助理
prompt_a = "你是一個專業客服助理，請用條列式回答。"

# Prompt B：詩人
prompt_b = "你是一個詩人，請用優美的散文回答。"

question = "請介紹一下 VPN 的用途"

print("=== 客服助理 ===")
print(ask(prompt_a, question))

print("\n=== 詩人 ===")
print(ask(prompt_b, question))