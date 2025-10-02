# LLM API Gateway (Day18)

本專案實作了一個統一的 LLM API 閘道器，負責模型路由、流量限制，並與檢索增強生成（RAG）服務整合。
前端統一呼叫 /ask，由 API Gateway 在後端負責 模型路由 / 限流 / 觀測；並與 RAG 檢索服務整合，回傳人性化答案。

## 專案結構

```yaml
day18_llm_gateway/
├─ gateway/
│ └─ main.py # FastAPI：/ask 端點 + 流量限制 / 日誌 / 監控指標
├─ services/
│ └─ retrieval_service.py # RAG 檢索（向量嵌入 + 搜尋）
├─ frontend/
│ └─ index.html # 展示用前端（選用）
├─ .env.sample # 環境變數範本
└─ requirements.txt # Python 相依套件
```

## 快速啟動（Conda）

建立並啟用 Conda 環境（Python 3.11）：

```bash
# 1) 建立與啟用 conda 環境（Python 3.11）
conda create -n day18_llm_gateway python=3.11 -y
conda activate day18_llm_gateway

# 2) 安裝套件
pip install -r requirements.txt

# 3) 設定環境變數
cp .env.sample .env
# 打開 .env，填入 OPENAI_API_KEY 等設定

# 4) 啟動服務
uvicorn gateway.main:app --reload --port 8000
```

> 若使用 Mamba 或 Micromamba，可執行：
> mamba create -n llm-gateway python=3.11 -y && mamba activate llm-gateway

## 環境變數（.env.sample）

```bash
OPENAI_API_KEY=
CHAT_MODEL=gpt-4o-mini
OPENAI_TIMEOUT=20
RETRIEVAL_TOPK=3
```

## 驗證服務

- API 文件：http://localhost:8000/docs
- 健康檢查：http://localhost:8000/healthz
- 監控指標（Prometheus）：http://localhost:8000/metrics

## cURL 測試範例

```bash
curl -X POST "http://localhost:8000/ask" \
 -H "Content-Type: application/json" \
 -H "X-Request-Id: demo-123" \
 -d '{"question":"加班規則是什麼？"}'

curl -X POST "http://localhost:8000/ask" \
 -H "Content-Type: application/json" \
 -H "X-Request-Id: demo-123" \
 -d '{"question":"加班規則是什麼？","temperature":0.2,"top_k":3}'
```

## 📈 Metrics

本專案已內建 Prometheus 指標與 /metrics 端點（text exposition format）。
Middleware 會自動量測所有路由（已排除 /metrics 自身），並記錄請求數、延遲與錯誤。

#### 已暴露的指標

| 名稱                               | 型別      | Label                   | 說明                                         |
| ---------------------------------- | --------- | ----------------------- | -------------------------------------------- |
| `gateway_requests_total`           | Counter   | `route, method, status` | 每個路由的請求次數（含狀態碼）               |
| `gateway_request_duration_seconds` | Histogram | `route, method`         | 請求延遲直方圖（可推 p50/p95/p99）           |
| `gateway_errors_total`             | Counter   | `route, type`           | 錯誤次數（如 `http`、`unhandled`、自訂類型） |

> 小提醒：若你也想忽略 /healthz 的量測，可在 middleware 內加判斷略過。

## 注意事項（正式環境）

- 目前的流量限制為教學用的記憶體內存，重啟後會清空，且無法跨機器共享。
- 正式環境建議改用 Redis、Nginx 或雲端閘道器。
- 建議導入 JWT 或每個租戶獨立的 API Key、結構化日誌，以及基本監控指標（請求數、延遲、錯誤率、快取命中率）。
