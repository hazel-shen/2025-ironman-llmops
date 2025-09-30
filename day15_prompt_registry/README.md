# Day15 - Prompt Registry Demo

這個範例示範如何用 設定檔 (YAML) 管理 Prompt，並透過 PromptRegistry 載入後渲染，再送到 LLM。
同時配合 pytest 做基本測試，確保 Prompt 更新後不會退化。

## 安裝與執行

可以選擇 **venv** 或 **conda** 來建立環境。

### 使用 venv

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 使用 conda

```bash
# 建立 conda 環境
conda create -n day15_prompt_registry python=3.11 -y
conda activate day15_prompt_registry

# 安裝依賴
pip install -r requirements.txt
```

## 📂 專案結構

```graphql
day15_prompt_registryo/
./
├── README.md                 # 專案介紹與使用說明
├── demo_different_prompt.py  # Demo：同題比較 v1 / v2 Prompt 回覆差異
├── demo_generate_2_prompts.py# Demo：示範一次產生兩個不同風格的 Prompt
├── gateway.py                # FastAPI 入口，對外提供 /ask /versions /prompts
├── prompts/                  # Prompt 模板存放處
│   ├── prompts_v1.yaml       # Prompt 定義 v1
│   └── prompts_v2.yaml       # Prompt 定義 v2
├── pytest.ini                # 測試設定檔
├── registry/
│   ├── __init__.py           # 模組初始化
│   └── registry.py           # PromptRegistry：載入/渲染/列出 Prompt
├── requirements.txt          # 套件需求清單
└── tests/
    ├── conftest.py           # 測試共用設定
    ├── test_prompts.py       # 測試 prompts 渲染
    └── test_registry.py      # 測試 PromptRegistry 功能

```

## 使用方式

### 1. 跑 pytest 測試

確保 PromptRegistry 和 Prompts 都能正常載入與渲染：

```bash
pytest -q
```

輸出結果：

```bash
❯ pytest -q -v

=============================================================== test session starts ===============================================================
platform darwin -- Python 3.11.13, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/hazel/Documents/github/2025-ironman-llmops/day15_prompt_registry
configfile: pytest.ini
plugins: anyio-4.11.0
collected 18 items

tests/test_prompts.py ........                                                                                                              [ 44%]
tests/test_registry.py ..........                                                                                                           [100%]

=============================================================== 18 passed in 0.03s ================================================================

```

### 2. 執行 Demo 程式 （Optional)

直接渲染 v1 與 v2 的 FAQ Prompt，觀察差異：

```bash
python demo_generate_2_prompts.py
```

輸出範例：

```bash
[FAQ v1]
你是一個專業客服助理，請根據以下文件回答...

[FAQ v2]
你是一個客服助理。依據下列文件回答問題並輸出 JSON...
```

### 啟動 Gateway (FastAPI + OpenAI)

在專案根目錄建立 .env：

```bash
OPENAI_API_KEY=sk-xxxxxx
```

啟動 Gateway：

```bash
uvicorn gateway:app --reload --port 8000
```

開啟另外一個 Terminal 測試請求，可以在 `Header` 帶入不同版本（有 v1 / v2）：

```bash
❯ curl -s http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -H "X-Prompt-Version: v1" \
  -d '{
    "question": "公司的總部在哪？",
    "context": "文件：公司資訊…",
    "prompt_name": "faq",
    "model": "gpt-4o-mini"
  }' | jq .

{
  "answer": "- 文件中未提及",
  "prompt_id": "faq:v1",
  "model": "gpt-4o-mini"
}
```
