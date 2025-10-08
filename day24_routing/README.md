# Day24 — 分類器式路由（Classifier Router）Demo

> 目標：讓系統先看「檢索訊號」再決定是 **直接用 KB 回**，還是 **丟給小模型**，在 **成本 × 延遲 × 品質** 之間取得平衡。

## 專案結構

```yaml
day24_routing/
├── README.md                         # 專案說明：目標、啟動方式、路由規則、Metrics、示例指令
├── app/                              # 服務端核心程式碼
│   ├── __init__.py                   # 將 app/ 視為 Python 套件，方便 tests 匯入
│   ├── llm_small.py                  # 小模型封裝：組裝回答、估算 tokens/cost（fallback 用）
│   ├── main.py                       # FastAPI 入口：/ask、/metrics、/healthz；整合 retriever + router
│   ├── metrics.py                    # Prometheus 指標：請求數、延遲、路由計數、token 與成本
│   ├── models.py                     # Pydantic Schema：Request/Response、Signals、RouteDecision 等
│   ├── retriever.py                  # 檢索器：jieba 分詞 + TF-IDF；輸出 topK contexts 與檢索訊號
│   └── router.py                     # 路由規則：依 max/avg/num_docs 決定走 KB 或 Small Model
├── data/                             # Demo 用資料，專案啟動後需要手動匯入
│   ├── kb.jsonl                      # 知識庫（JSON Lines）：每行一筆 {id, text}
│   └── userdict.txt                  # jieba 自訂詞典：企業常用詞（請假流程、公司VPN…）
├── environment.yaml                  # Conda/Pip 依賴：fastapi、sklearn、jieba、pytest、prometheus-client…
└── tests/                            # 測試（pytest）
    ├── conftest.py                   # 測試前置：修正匯入路徑、自動載入 data/userdict.txt
    ├── test_end2end.py               # E2E：/healthz 與 /ask 全流程可用性
    ├── test_jieba_dict.py            # 驗證自訂詞典切詞是否生效（請假流程、公司VPN）
    ├── test_llm_small.py             # 小模型 fallback 行為：沒命中/低分命中/正常命中，回答與成本估算
    ├── test_retriever.py             # 檢索器：英文/中文 Query 是否命中正確 KB
    └── test_router.py                # 路由決策：max/avg 過門檻與邊界情境（小模型/KB）
```

## 🔑 是否需要 API Key？

本 Demo **完全不需要** OpenAI API Key。

- Retriever 用的是本地的 jieba + TF-IDF，不用呼叫外部 API。
- Router 是簡單的門檻分類器。
- 小模型 (llm_small.py) 僅是模板拼接回答與估算 Token，沒有連線到任何 LLM。

## Routing 規則（預設）：

- max_score ≥ 0.55 或 avg_topk ≥ 0.35 ，且 num_docs ≥ 1 → KB
- 否則 → 小模型

> 可以與 Day23 的增量更新相接：KB/索引更新後，Routing 規則自然反映新的檢索分數。

## 快速開始

```bash
conda env create -f environment.yaml
conda activate day24_routing

# 準備資料

mkdir -p data
cat > data/kb.jsonl <<'EOF'
{"id":"faq-001","text":"公司 VPN 設定：下載新版客戶端，並以 SSO 登入；首次登入需註冊 MFA。"}
{"id":"faq-002","text":"請假流程：登入 HR 系統提交假單，主管核准後會自動同步至行事曆。"}
{"id":"faq-003","text":"內部 Wi-Fi：SSID 為 Corp-5G，密碼由 IT 每季輪替，詳見內網公告。"}
{"id":"faq-004","text":"報帳規範：差旅需上傳發票影本，填寫報銷單並經部門主管審核。"}
{"id":"faq-005","text":"開發流程：所有新功能必須先建立 Pull Request，經至少兩人 Code Review 通過後才能合併。"}
{"id":"faq-006","text":"版本控制：主幹分支為 main，禁止直接推送，必須透過 Pull Request 流程合併。"}
{"id":"faq-007","text":"例行會議：每週一上午 10 點為團隊例會，需準備上週進度與本週計劃。"}
{"id":"faq-008","text":"IT 支援：若遇到電腦故障或帳號問題，請至 IT Helpdesk 提交工單。"}
{"id":"faq-009","text":"年度健檢：公司會於 9 月安排員工年度健康檢查，報名方式會提前寄送 Email。"}
{"id":"faq-010","text":"出差規定：出差需事先填寫申請單，並附上行程表，經主管批准後方可訂票。"}
EOF

# 建立自訂詞典（提升中文檢索準確度）
cat > data/userdict.txt <<'EOF'
公司VPN
VPN
SSO
MFA
請假流程
請假
報帳規範
出差規定
出差補助
內部Wi-Fi
Wi-Fi
版本控制
Pull Request
Code Review
年度健檢
健康檢查
例行會議
IT支援
Helpdesk
EOF

# 執行服務
uvicorn app.main:app --reload --port 8000

## 測試
pytest -q
```

## 呼叫範例

```bash
curl -s http://localhost:8000/ask \
 -H "content-type: application/json" \
 -d '{"query":"如何設定公司 VPN？","top_k":3}' | jq

# Wi-Fi
curl -s http://localhost:8000/ask \
  -H "content-type: application/json" \
  -d '{"query":"內部 Wi-Fi 密碼是多少？","top_k":3}' | jq

# 出差補助（模糊關聯：出差規定 + 報帳規範）
curl -s http://localhost:8000/ask \
  -H "content-type: application/json" \
  -d '{"query":"我要怎麼申請出差補助？","top_k":3}' | jq

# 健檢報名（模糊關聯：年度健檢，但問題不同）
curl -s http://localhost:8000/ask \
  -H "content-type: application/json" \
  -d '{"query":"公司的健檢報名流程是？","top_k":3}' | jq
```

## 調參建議

### 📊 測試資料規模大小的影響

- 小 KB（3–10 條）

  - 分數差異大，max_score 容易拉高。
  - 大部分 Query 都會被判斷走 KB。
  - 適合 Demo，邏輯清楚。

- 中等 KB（50–100 條）

  - 命中率更真實，avg_topk 會被稀釋，低分數情境更多。
  - 有些 Query 會因為平均分數不足 → 被導到小模型。
  - 適合展示「Routing 的價值」。

- 大型 KB（上千條以上）
  - max_score 常落在 0.2–0.5，需要重新調整 Router 閾值。
  - 建議替換為 BM25 / 向量檢索 (FAISS, Weaviate)。

### ⚡ 對效能的影響

- 初始化成本

  - Retriever 啟動時會先載入並向量化 KB。
  - 條目數越多，初始化時間越久。幾百筆幾乎無感，幾萬筆就會明顯。

- 查詢延遲

  - 每次查詢都要計算與 KB 的相似度。
  - 幾千筆以內仍然很快；上萬筆可能會導致 /ask 延遲上升。

- 記憶體消耗
  - TF-IDF 向量矩陣大小 ≈ #docs × #features。
  - KB 條目越多，佔用的記憶體越大。
  - Demo 預設 max_features=10,000，小 KB 問題不大，大 KB 可能需要更好的的硬體裝置。

## 🈶 中文檢索優化 (jieba)

由於 scikit-learn 預設的 **英文 tokenizer** 對中文無法正確分詞，導致檢索分數偏低。  
我們將 tokenizer 換成 **jieba 中文分詞** 後，檢索效果大幅提升。

| Query                     | 預設 TF-IDF (英文 tokenizer)    | Jieba 分詞 (中文 tokenizer)  | 差異說明                                                                                                       |
| ------------------------- | ------------------------------- | ---------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **如何設定公司 VPN？**    | `max≈0.24, avg≈0.08` → 走小模型 | `max≈0.72, avg≈0.51` → 走 KB | 英文 tokenizer 無法切「公司/VPN/登入」，導致分數偏低；jieba 能正確分詞，信號提升明顯。                         |
| **我要請假要怎麼辦？**    | `max≈0.18, avg≈0.06` → 走小模型 | `max≈0.65, avg≈0.43` → 走 KB | 預設 tokenizer 把「請假」拆成單字，無法和 KB「請假流程」對上；jieba 能命中關鍵詞「請假」。                     |
| **公司 Wi-Fi 密碼多少？** | `max≈0.21, avg≈0.07` → 走小模型 | `max≈0.68, avg≈0.40` → 走 KB | 英文 tokenizer 把「Wi-Fi」保留，但「公司/密碼」沒對應；jieba 把「公司」「Wi-Fi」「密碼」分出來，檢索效果提升。 |

> ✅ 中文專案建議直接使用 **jieba tokenizer** 或其他中文分詞器，避免 Query 落空被錯誤路由到小模型。

## 📈 Metrics

系統會輸出 Prometheus 格式的指標，方便後續接入 Grafana 或其他監控工具。

- day24_requests_total：API 請求數量
- day24_request_latency_seconds：延遲直方圖（可算 P95/P99）
- day24_route_decision_total{target="kb|small_model"}：路由決策次數統計
- day24_tokens_total{role="prompt|completion"}：Token 使用量
- day24_cost_usd_total：小模型成本估算

### 呼叫範例

```bash
# 直接查看前 20 行
❯ curl -s http://localhost:8000/metrics | head -n 20
# HELP day24_requests_total Total API requests
# TYPE day24_requests_total counter
day24_requests_total{route="/ask"} 3.0

# HELP day24_request_latency_seconds Request latency histogram
day24_request_latency_seconds_bucket{le="0.1",route="/ask"} 2.0
day24_request_latency_seconds_bucket{le="0.3",route="/ask"} 3.0
day24_request_latency_seconds_count{route="/ask"} 3.0

# HELP day24_route_decision_total Route decision counts
day24_route_decision_total{target="kb"} 2.0
day24_route_decision_total{target="small_model"} 1.0

# 查看路由決策分布
❯ curl -s http://localhost:8000/metrics | grep day24_route_decision_total
# HELP day24_route_decision_total Routing target
# TYPE day24_route_decision_total counter
day24_route_decision_total{target="kb"} 2.0
day24_route_decision_total{target="small_model"} 1.0

# 查看 Token 使用量
❯ curl -s http://localhost:8000/metrics | grep day24_tokens_total
# HELP day24_tokens_total Estimated tokens used
# TYPE day24_tokens_total counter
day24_tokens_total{role="prompt"} 7.0
day24_tokens_total{role="completion"} 42.0
```
