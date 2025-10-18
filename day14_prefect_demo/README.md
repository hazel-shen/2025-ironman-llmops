# Day 14 – Prefect 小型 Demo（LLMOps：RAG Pipeline 自動化）

這個範例把「員工手冊 → 清洗 → Chunk → Embedding →（模擬）向量索引」做成一條 Prefect Flow:

#### 步驟

1. 讀取員工手冊 (worker_manual.txt)
2. 文件清洗 & Chunking
3. Embedding → 產生向量索引 (data/vector_index.json)
4. 查詢相關內容

#### 支援：

- 本地一次性執行
- （可選）建立 Deployment：每日 02:00（Asia/Taipei）自動跑
- 最小檢索腳本（cosine similarity）

## 專案結構

```graphql
day14_prefect_demo/
├── data/
│   ├── worker_manual.txt      # 測試用的員工手冊
│   └── vector_index.json      # Pipeline 輸出：向量索引
│
├── flows/
│   ├── __init__.py
│   ├── daily_pipeline.py      # Prefect Flow：每日更新 RAG pipeline
│   └── deploy.py              # (進階) 部署到 Prefect UI/Cloud
│
├── scripts/
│   ├── query.py               # 查詢：假向量版本（無需 API key）
│   ├── query_with_openai.py   # 查詢：真實 OpenAI Embedding
│   └── watch_and_trigger.py   # 檔案監控，修改後自動觸發流程
│
├── utils/
│   ├── __init__.py
│   ├── cleaning.py            # 文件清洗
│   ├── chunking.py            # 文件切片
│   └── embeddings.py          # Embedding / OpenAI API 呼叫
│
├── .env.example               # 環境變數範例
├── requirements.txt           # 需要安裝的套件
└── README.md                  # 專案說明文件
```

## 環境以及安裝

你可以選擇 conda 或 pip 來建立環境。

### 使用 conda（推薦）

```bash
# 建立 conda 環境
conda create -n day14_prefect_demo python=3.10 -y
conda activate day14_prefect_demo

# 安裝套件
pip install -r requirements.txt
cp .env.example .env
# 如要使用真實 OpenAI 向量，填入 OPENAI_API_KEY，並將 USE_FAKE_EMBEDDINGS 設為 false
```

建議的 requirements.txt：

```txt
prefect==2.20.17
pydantic==2.7.1
pydantic-core==2.18.2
griffe>=0.44,<1.0
httpx<0.28,>=0.27
openai>=1.40.2
python-dotenv==1.0.1
beautifulsoup4==4.12.3
```

### 🔧 特別注意：

```yaml
- httpx<0.28：避免 proxies 參數錯誤。
- pydantic==2.7.1：與 Prefect 2.19.x 相容。
- griffe：Prefect 依賴的額外套件。
```

### 使用 pip (venv)

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# 如要使用真實 OpenAI 向量，填入 OPENAI_API_KEY，並將 USE_FAKE_EMBEDDINGS 設為 false
```

## 一次性執行（本地）

```bash
python -m flows.daily_pipeline
# 成功後會產生 data/vector_index.json
```

## 查詢（最小測試）

#### (A) 用假向量（不需 API key）

```bash
python scripts/query.py "加班規則"
```

#### (B) 用 OpenAI Embedding（真實向量）

```bash
python scripts/query_with_openai.py "加班規則"
```

## 🛠️ 進階：使用 Prefect UI 建立 Deployment + 每日 02:00 自動排程

如果要在 Prefect Cloud 或 本地 UI 管理流程：

```bash
prefect config set PREFECT_API_URL=http://127.0.0.1:4200/api
prefect server start
```

> 若本機 prefect server start 出現 SQLite database is locked，建議重啟或改用外部 Postgres（附連結或一行註記即可）。

然後部署：

```bash
python -m flows.deploy
```

接著在 UI 畫面的 `Deployments` tab 中可看到 daily_rag_update (Flow nmae) / daily-2am (Deployment name)。

## 👀 本機自動監控 (可選)

除了排程，你也可以在 修改 data/worker_manual.txt 後自動觸發流程。

#### 啟動監控腳本

```bash
pip install watchdog
python scripts/watch_and_trigger.py
```

#### 預設行為

- 監控 data/worker_manual.txt
- 檔案被修改時，自動執行 flows/daily_pipeline.py

#### 切換成觸發 Prefect Deployment

如果已經有 deployment（例如 daily_rag_update/daily-2am），可以改成用 deployment 方式觸發：

```bash
export USE_PREFECT_DEPLOYMENT=true
export PREFECT_DEPLOYMENT_NAME="daily_rag_update/daily-2am"
python scripts/watch_and_trigger.py
```

#### 其他參數

```bash
# 修改監控的檔案路徑
export WATCH_FILE="data/worker_manual.txt"

# 設定去彈跳秒數 (避免一次儲存多次觸發)
export DEBOUNCE_SEC=1
```
