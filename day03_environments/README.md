# Day03 - Environment Preparation

## 啟動

#### 測試 embedding 腳本

```bash
# 用 conda 創建一個新的專案環境
❯ conda env create -f ./env/environment.yml

# 啟動專案環境
❯ conda activate day03_environments

# 把 OpenAI API key 寫到環境變數裡
#（僅本次 session 有效，若要長期使用可寫進 `.env` 或 shell 啟動檔）
export OPENAI_API_KEY=sk-xxxxxxx

# 呼叫測試程式碼
❯ python test_embedding.py
Cosine similarity: 0.2016753894756205
```

#### 測試 `/ask` API

兩種方式：

1. 直接用 `uvicorn` 跑起來

```bash
uvicorn src.app:app --reload --port 8000
```

2. `Docker` 打包 `Image` 後跑起來

```bash
# 先 build image，第一次打包會很慢沒關係
docker build -t day03_environments -f docker/Dockerfile .

# 先把 API key 寫進去設定檔案
echo "OPENAI_API_KEY=sk-proj-XXX(你的 OpenAI API key)" >> .env

# docker run 啟動容器
docker run -it --rm -p 8000:8000 \
	 -v "$(pwd)/src:/app/src" \
	 -v "$(pwd)/.env:/app/.env:ro" \
	 day03_environments

# 測試 /ask API，繁體中文要先編碼，否則會被判定成非法的 HTTP request
curl -G --data-urlencode "q=什麼是LLMOps？請用繁體中文回答我" http://localhost:8000/ask
```
