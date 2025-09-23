#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
01_embed_quickcheck.py
目的：
- 最小可跑版（smoke test）：確認環境變數、網路、openai 套件正常
- 取得一段文字的 embedding，印出維度長度

用法：
  conda activate day09
  cp .env.example .env  # 並填上 OPENAI_API_KEY
  python 01_embed_quickcheck.py
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("沒有找到 OPENAI_API_KEY，請在 .env 設定！")

    # 使用環境變數建立 Client（建議統一風格：隱式讀取即可）
    client = OpenAI()

    text = "RAG pipeline 需要清洗與切片"
    resp = client.embeddings.create(model="text-embedding-3-small", input=text)
    vec = resp.data[0].embedding
    print(f"✅ 取得 embedding 成功，維度長度：{len(vec)}")

if __name__ == "__main__":
    main()
