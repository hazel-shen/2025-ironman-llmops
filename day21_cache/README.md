# LLM Cache Demo

最小可行的 LLM 快取 Demo，包含：

- Prompt 字串快取（Redis）
- 語意快取（Embedding Cache；支援 Redis 持久化）
- 指標收集（Prometheus `/metrics` 與 `/metrics/json`）
- FastAPI 服務：`/ask`, `/health`

## 🚀 快速開始

### 0) 啟動 Redis

```bash
# 1. 建立資料夾（避免權限問題）
mkdir -p ./data/redis

# 2. 啟動 Redis
docker compose up -d

# 3. 測試
redis-cli ping   # 回 PONG

# 4. 結束測試後 shut down 並清除 volume
docker compose down -v
```

### 1) 建立並啟動 Conda 環境

```bash
conda env create -f environment.yaml
conda activate day21_cache

# 停用環境
conda deactivate

# 查看所有環境
conda env list

# 刪除環境（⚠️ 慎用）
conda env remove -n day21_cache

# 更新環境（當 environment.yml 有修改時）
conda env update -f environment.yml --prune
```

### 2) 設定環境變數

```bash
cp .env.example .env
# 編輯 .env，把你的 OPENAI_API_KEY 填入
```

### 3) 啟動 API

```bash
uvicorn api.main:app --reload
```

### 4) 測試 API

```bash
# 問一次 → LLM 真實回答，並存進 Prompt Cache + Embed Cache
curl -X POST localhost:8000/ask -H "content-type: application/json" -d '{"question":"什麼是快取？"}'

# 再問類似問題 → 可命中快取
curl -X POST localhost:8000/ask -H "content-type: application/json" -d '{"question":"請解釋快取是什麼"}'

# 檢查健康狀態
curl localhost:8000/health

# 檢查指標（Prometheus 格式）
curl localhost:8000/metrics

# 檢查指標（JSON 格式）
curl localhost:8000/metrics/json
```

## 🧪 測試（pytest）

專案附帶測試，涵蓋 API、快取與 Metrics。
測試已 mock OpenAI（不會對外呼叫、不花錢），並會在每次執行前後自動清空 Redis。

### 1) 安裝相依 (Optional, Conda 已經包進去)

```bash
pip install -U pytest pytest-asyncio httpx pytest-cov
```

### 2) 執行測試

```bash
# 全部測試
pytest -vv

# 指定單一檔案
pytest -vv tests/test_api.py
```

### 3)測試特點

- 不用啟動 uvicorn，httpx 直接以 in-process 呼叫 FastAPI app。
- Redis 每個測試獨立連線、測前後 flushdb()，避免污染。
- Mock LLM：chat 與 embed 固定回傳假資料，避免外部 API。
- Metrics 測試會驗證 /metrics 與 /metrics/json 正確更新。

## 🔧 管理 Redis 快取

在這個專案裡，我們把 Prompt Cache 和 Embedding Cache 都存在 Redis。
有時候需要清掉資料來測試命中率或重置環境，可以用以下幾種方式：

1. 清空整個 Redis

```bash
⚠️ 會刪掉所有資料（包含 prompt / embed cache 等）：

redis-cli FLUSHDB     # 清除當前資料庫 (預設 DB 0)
redis-cli FLUSHALL    # 清除所有資料庫
```

2. 只清除特定快取

如果只想清除某類 cache，可以用 key pattern：

```
# 清除 Prompt Cache
redis-cli --scan --pattern "prompt_cache:*" | xargs redis-cli DEL

# 清除 Embedding Cache
redis-cli --scan --pattern "embed_cache:*" | xargs redis-cli DEL
```

## 📂 專案結構

```yaml
day21_cache/
.
├── README.md                # 專案說明文件
├── __init__.py              # 標記根目錄為 Python package（通常空白即可）
│
├── api/                     # API 層（FastAPI / RESTful 入口）
│   ├── __init__.py
│   ├── main.py              # API 主入口（啟動 FastAPI app）
│   └── routers/             # 各功能的路由拆分（ex: /health, /cache）
│
├── core/                    # 核心設定與共用邏輯
│   ├── __init__.py
│   ├── config.py            # 環境變數 & 設定管理
│   └── metrics.py           # 監控 & 指標（Prometheus/Grafana）
│
├── data/                    # 資料相關
│   └── redis/               # Redis 資料存放區（可能掛載 volume）
│
├── docker-compose.yml       # Docker Compose 定義（Redis, API 等服務）
├── environment.yaml         # Conda 環境設定檔
│
├── models/                  # 資料模型
│   ├── __init__.py
│   └── schemas.py           # Pydantic schema（定義 API 輸入輸出）
│
├── pytest.ini               # pytest 設定
│
├── scripts/                 # 工具腳本
│   └── init_index.py        # 初始化索引（ex: 建立 Redis/向量庫 index）
│
├── services/                # 服務層（封裝商業邏輯）
│   ├── __init__.py
│   ├── cache.py             # Prompt/回應快取
│   ├── embed_cache_redis.py # Embedding Cache with Redis
│   ├── llm.py               # 與 LLM API 互動（OpenAI / Anthropic）
│   └── redis_client.py      # Redis 客戶端連線封裝
│
└── tests/                   # 測試
    ├── conftest.py          # pytest 共用設定/fixture
    ├── test_api.py          # 測 API 行為
    ├── test_embed_cache_redis.py # 測試 embedding cache
    ├── test_health.py       # 健康檢查 endpoint 測試
    ├── test_metrics.py      # 測試 metrics 輸出
    └── test_prompt_cache.py # 測試 prompt cache 基本功能
```

## 🔧 常見調整

- `core/config.py` → 可調整 `CACHE_TTL`, `EMBED_SIM_THRESHOLD`
- `.env` → 設定 `OPENAI_API_KEY`
- 語意快取：目前支援 `Redis`（持久化），大量資料時可改用 `FAISS/pgvector`
