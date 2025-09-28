# day14_dagster_demo

用 **Dagster** 實作最小化的 RAG Pipeline（資產導向）：  
`worker_manual.txt → clean → chunk → embed → vector_index.json`

支援：

- 每日 **02:00 (Asia/Taipei)** 自動排程
- **檔案變更監控**（修改 `worker_manual.txt` 會自動觸發重新產生 index）

---

## 🚀 環境建置

### 1. 建立 conda 環境

```bash
conda create -n day14_dagster_demo python=3.10 -y
conda activate day14_dagster_demo
```

### 2. 安裝依賴

```bash
pip install -r requirements.txt
```

### 3. 設定環境變數

```bash
cp .env.example .env
```

編輯 .env，填入你的 OpenAI API Key：

```env
OPENAI_API_KEY=sk-xxxx
QUERY_EMBEDDING_MODEL=text-embedding-3-small
```

## ▶️ 開發模式啟動

```bash
dagster dev -m defs
```

- UI 入口： http://127.0.0.1:3000

## ⏱ 手動一次性執行

```bash
dagster asset materialize -m defs --select "*"
```

會自動跑完整流程，並在 data/vector_index.json 產生最新索引。

## ✅ 開啟每日 02:00 自動排程

#### 方法 A：使用 Dagster Dev（推薦）

```bash
dagster dev -m defs
```

- 打開 http://127.0.0.1:3000
- 點選上面選單的 `Deployment` -> `Schedules`
- 找到 `daily_2am_taipei` → 切換 `Running` 為 ON

只要這個 `Process` 在跑，`Dagster` Daemon 就會在每天 02:00 (Asia/Taipei) 自動觸發 pipeline。

#### 方法 B：純 CLI

> ⚠️ 若用 CLI，需要額外啟動 daemon：

```bash
# 設定 DAGSTER_HOME 變數（放在家目錄下的 dagster_home 資料夾）
export DAGSTER_HOME="$HOME/dagster_home"

# 建立資料夾
mkdir -p "$DAGSTER_HOME"

# 建立最小設定檔
cat > "$DAGSTER_HOME/dagster.yaml" << 'YAML'
storage:
  sqlite:
    base_dir: "~/.dagster"
run_coordinator:
  module: dagster._core.run_coordinator
  class: DefaultRunCoordinator
YAML

# 如果正常輸出 instance 資訊，代表 $DAGSTER_HOME 已經生效
dagster instance info

# 開 UI（只負責前端）
dagster-webserver -m defs

# 另開一個終端機，跑 Daemon（負責 schedules / sensors）
dagster-daemon run

# 啟用每日 02:00 schedule
dagster schedule start -m defs daily_2am_taipei
# 確認啟用成功
dagster schedule list -m defs
```

## ✅ 開啟檔案變更 Sensor

如果要在 worker_manual.txt 修改後自動重跑：

#### 方法 A：在 Dagster UI 啟用

- 進入 http://127.0.0.1:3000
- 左側選單 → Sensors
- 找到 on_worker_manual_change → 切換 ON

#### 方法 B：CLI

```bash
dagster sensor start -m defs on_worker_manual_change
```

同樣需要 dagster-daemon run 來常駐執行。

## 📂 專案結構

```bash
day14_dagster_demo/
├── assets/
│ ├── **init**.py
│ ├── common.py # 共用函式：路徑、清洗、切片
│ ├── raw_text.py # 資產：讀取原始檔
│ ├── cleaned_text.py # 資產：清洗文本
│ ├── chunks.py # 資產：切片
│ ├── vectors.py # 資產：向量化 (OpenAI Embeddings)
│ └── vector_index.py # 資產：輸出 JSON 索引
├── data/
│ └── worker_manual.txt # 測試檔案
├── defs.py # 定義資產 + job + schedule + sensor
├── requirements.txt
├── .env.example
└── README.md
```

## 📝 輸出範例

data/vector_index.json

```json
{
  "meta": {
    "source": "worker_manual.txt",
    "generated_at": "2025-09-09T05:00:00Z",
    "model": "text-embedding-3-small"
  },
  "items": [
    {
      "id": 0,
      "chunk": "第一章：出勤規範...",
      "vector": [0.0123, -0.9876, ...]
    }
  ]
}
```
