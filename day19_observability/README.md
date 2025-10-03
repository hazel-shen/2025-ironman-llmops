# 📊 LLM Observability Demo (FastAPI + Prometheus + Grafana)

這是一個最小可行的 LLM Observability 範例專案，透過 FastAPI 包裝 OpenAI，並輸出 Prometheus Metrics，最後用 Grafana Dashboard 視覺化。

## 🚀 功能

`/ask`：呼叫 OpenAI API（真實執行），並回傳 Latency、Token 使用量與成本
`/metrics`：Prometheus exporter，輸出 LLM 相關 metrics

預設提供的 metrics：

- `llm_requests_total`：請求數量
- `llm_tokens_total`：Token 使用量（prompt/completion 分開）
- `llm_request_latency_seconds`：延遲直方圖（可算 P95/P99）
- `llm_cost_usd_total`：累積成本（USD）
- `llm_errors_total`：錯誤統計

## 📂 專案結構

```yaml
day19_observability/
├─ app/
│  ├─ app.py              # FastAPI + Prometheus exporter
│  ├─ requirements.txt
│  └─ Dockerfile
├─ tests/
│  └─ test_requests.py    # 測試腳本
├─ docker/
│  ├─ prometheus.yml
│  └─ grafana/
│     └─ provisioning/
│        ├─ dashboards/
│        │  ├─ dashboard.yml
│        │  └─ llm_observability.json
│        └─ datasources/
│           └─ datasource.yml
├─ environment.yaml        # Conda 環境設定
├─ .env                   # 環境變數 (不要上傳)
├─ .env.example           # 環境變數範例
├─ docker-compose.yml
├─ README.md
└─ .dockerignore
```

⚙️ 環境變數設定（.env）

```env
APP_PORT=8000
PROM_PORT=9090
GRAFANA_PORT=3000

GRAFANA_USER=admin
GRAFANA_PASS=admin

# OpenAI API
OPENAI_API_KEY=你的_API_KEY
OPENAI_MODEL=gpt-4o-mini
OPENAI_TIMEOUT=30
```

⚠️ 請確保 .env 沒有被 commit 上 GitHub（已建議在 .gitignore 忽略）。

## ▶️ 兩種使用模式

| 模式                     | 技術                                            | 適合用途                   | 是否可看 Grafana            |
| ------------------------ | ----------------------------------------------- | -------------------------- | --------------------------- |
| **方法一：開發模式**     | Conda + FastAPI                                 | 本地測試 API、Debug        | ❌ 只能看 `/metrics` 純文字 |
| **方法二：完整觀測模式** | Docker Compose (FastAPI + Prometheus + Grafana) | 完整監控、視覺化 Dashboard | ✅                          |

### 方法一：開發模式（Conda，本機測試 app.py 用的）

1. 建立環境並啟用

```bash
cd day19_observability
conda env create -f environment.yaml
conda activate day19_observability
```

2. 確保 `.env` 已設定好（至少要有 `OPENAI_API_KEY`）。

3. 測試 API：

```bash
curl -X POST http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"用三點解釋 RAG"}]}'
```

4. 查看 metrics：

```bash
curl http://localhost:8000/metrics | head -50
```

測試完不需要用到的時候：

```bash
conda remove --name day19_observability --all
```

> ⚠️ 注意：這會刪除整個環境與安裝的套件。

### 方法二：完整觀測模式（Docker Compose）

1. 建置並啟動容器

> 適合完整觀測，包括 Latency P95、Token 消耗趨勢、成本走勢等。

```bash
docker compose up -d --build
```

2. 測試 API

```bash
curl -X POST http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"用三點解釋 RAG"}]}'
```

範例回應：

```json
{
  "model": "gpt-4o-mini",
  "latency_s": 0.85,
  "prompt_tokens": 120,
  "completion_tokens": 180,
  "cost_usd": 0.00021,
  "answer": "RAG 是 Retrieval-Augmented Generation..."
}
```

3. 查看 Metrics

```bash
curl http://localhost:8000/metrics
```

範例輸出：

```bash
# HELP llm_requests_total Total LLM requests
# TYPE llm_requests_total counter
llm_requests_total{model="gpt-4o-mini"} 9.0
llm_requests_total{model="gpt-4o"} 2.0
llm_requests_total{model="gpt-4.1"} 1.0
# HELP llm_tokens_total Total tokens used
# TYPE llm_tokens_total counter
llm_tokens_total{model="gpt-4o-mini",type="prompt"} 265.0
llm_tokens_total{model="gpt-4o-mini",type="completion"} 435.0
llm_tokens_total{model="gpt-4o",type="prompt"} 57.0
llm_tokens_total{model="gpt-4o",type="completion"} 641.0
llm_tokens_total{model="gpt-4.1",type="prompt"} 28.0
```

4. 進入介面

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
  （帳號密碼見 .env）

> ⚠️ Prometheus 會定期抓 /metrics，Grafana 會自動載入 Dashboard，能看到 Latency / Tokens / Cost 曲線。

5. 停止但保留容器：

```bash
docker compose stop
```

6. 停止並刪除容器與 network：

```bash
docker compose down
```

7. 若要連同 volume 一起刪除（⚠️ 資料會消失）：

```bash
docker compose down -v
```

---

## 📊 Grafana Dashboard

專案內已提供簡單的 Dashboard JSON：

- Requests 總數
- Latency P95 曲線
- Token 使用量
- 成本走勢

匯入後即可快速查看。

## 🧪 測試腳本

專案內有 `tests/test_requests.py`，會打幾個 API 並顯示 metrics 變動。

執行方式：

```bash
python tests/test_requests.py
```

範例輸出：

```bash
✅ gpt-4o-mini 回答：RAG 是一種檢索增強生成技術... (tokens=15+120, cost=0.00013$)
✅ gpt-4o-mini 回答：RAG stands for Retrieval... (tokens=12+80, cost=0.00008$)
✅ gpt-4o 回答：在金融產業，RAG 可以用於... (tokens=30+200, cost=0.0026$)

📊 Metrics 部分輸出：
llm_requests_total{model="gpt-4o-mini"} 2.0
llm_requests_total{model="gpt-4o"} 1.0
llm_tokens_total{model="gpt-4o-mini",type="prompt"} 27.0
llm_tokens_total{model="gpt-4o-mini",type="completion"} 200.0
llm_cost_usd_total{model="gpt-4o-mini"} 0.00021
llm_cost_usd_total{model="gpt-4o"} 0.0026
```

## 🛠️ 後續擴充

- 增加更多模型定價（目前支援 GPT-4o、GPT-4o-mini，可依需求擴充）
- 加入 Rate Limit/429 錯誤監控
- 調整 Latency Histogram buckets 以符合實際 SLA
- 接入 Node Exporter 監控 CPU/Mem
