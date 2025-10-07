# Day23：RAG 增量更新 + Registry（CLI）+ OpenAI Fine-tune Demo Repo

這個 Repo 可以直接在本機重現 **RAG 增量更新 → 打包 → 註冊入 Registry** 的流程。

## 功能：

- 用 **FAISS + JSONL** 建立可**增量更新**的知識庫（RAG）
- 以 CLI 進行 Top‑K 檢索並取回原文（供後續組裝成 LLM 上下文）
- 將產生的 **知識庫產物** 打包後，**註冊到 Day22 的 Model Registry**（共用同一 API，不需前端）
- 額外：支援將 KB 匯出成微調資料並送到 OpenAI Fine-tune API

> **重要前置條件**：本 Demo 涵蓋註冊到 `Registry` 的部分，需要先啟動你在 **Day22** 建立的 _Registry Demo API_，假設位於 `http://localhost:8000`，並支援 `POST /models/{name}/versions`（與你提供的 cURL 範例相同）。

---

## 📁 專案結構

```
day23_iteration/
.
├── Makefile                  # 常用指令集合（build / run / clean，會自動產生部分檔案）
├── README.md                 # 專案說明文件
├── data                      # <-- 程式會自己建立這個目錄
│   ├── ft_cursor.json        # fine-tune 任務游標（由 make ft-export 自動產生）
│   ├── kb-v1757915827.tar.gz # 知識庫封裝檔（由 make pack / make register 自動產生）
│   ├── kb.index              # 檢索索引檔（由 make index 自動產生）
│   ├── kb.jsonl              # 知識庫原始 JSONL 格式（由 make init 自動產生）
│   ├── kb_meta.json          # 知識庫中繼資料（由 make init 自動產生）
│   └── mappings.json         # 文件 ID 與索引對應關係（由 make init 自動產生）
├── docs
│   └── examples_10.jsonl     # 範例 QA 或訓練資料（要手動或 script 產生）
├── environment.yaml          # Conda 環境設定
├── scenarios                 # <-- 程式會自己建立這個目錄
│   └── open_ai               # 測試/場景設定（OpenAI 專用）
└── scripts
    ├── add_docs.py           # 新文件加入知識庫並更新索引
    ├── ft_prep_from_kb.py    # 從知識庫產生 fine-tune 訓練集
    ├── openai_finetune.py    # 呼叫 OpenAI API 進行 fine-tuning
    ├── pack_and_register.py  # 打包知識庫並註冊版本（Registry）
    ├── qa_templates.py       # 常用 QA Prompt 模板
    ├── search.py             # 測試檢索功能（從索引查詢）
    └── test_ft_model.py      # 驗證 fine-tune 模型效果
```

## 🚀 使用方式

### 0) 先啟動 Day22 的 **Registry Demo API**（必要）

> 若尚未啟動，請先回到 Day22 的 Repo 啟動（FastAPI + SQLite 版本即可）。

---

### 1) 建立環境 (with Conda)

```bash
make env
conda activate day23_iteration
```

### 2) 初始化資料夾與檔案

```bash
make init
```

### 3) 增量新增文件（會自動建立/更新 FAISS 索引）

這邊我已經有建立範例文件（`docs/examples_10.jsonl`）了，可以直接拿來使用。

```bash
make add
# 或自行執行
# python scripts/add_docs.py  --jsonl docs/examples_10.jsonl
```

### 4) 以 CLI 檢索（Top‑K）並回傳原文

```bash
make search q="請假規定有哪些？" k=3
# 或自行執行
# python scripts/search.py "規定有哪些？" --k 3
```

### 5) 打包 KB 並註冊到 Registry

> 記得先檢查有沒有 `faq-bot` 這個 model

```bash
# 看該 model 是否已有版本
curl -s http://localhost:8000/models/faq-bot/versions | jq
# 有回傳陣列（可能是空陣列 []）→ model 存在
# 回 404/錯誤 → model 可能不存在

# 建立 model - `faq-bot`
curl -sX POST http://localhost:8000/models \
  -H 'Content-Type: application/json' \
  -d '{"name":"faq-bot","description":"KB-backed FAQ bot"}' | jq
```

打包並註冊到 registry

```bash
# 僅打包，不送出註冊
make pack

# 打包 + 註冊（呼叫 Day22 Registry API）
make register
```

> 後續如需**切換 Stage（Staging/Production）**、搭配 Gateway 讀取「當前 Prod KB 版本」等，可延用 Day22 的 API 與流程。

---

## ⚠️ 常見坑位與建議

- **向量維度/模型不一致**：更換 embedding 模型會改變維度，需重建索引或維持一致設定。
- **中文語意表現**：`all-MiniLM-L6-v2` 足夠示範；正式專案可評估 bge‑m3 / jina‑embeddings 等模型。

---

## 把 KB 丟入 OpenAPI fine-tune （可選）

```bash
# 0) 準備
export OPENAI_API_KEY=sk-...            # 先設好金鑰
make add # (Optional) 如果有新增資料的話，先做一次增量更新

# 1) 從 KB 匯出「本次新增」→ 產生 scenarios/b_lora_sft/train_new.jsonl
make ft-export

# (Optional) 如果有新增或刪除訓練資料 、模板等，要先把舊的 data/ft_cursor.json 重置
# 若不重置，系統可能會誤以為資料沒變，導致訓練檔不更新
make ft-reset


# 2) 直接建立微調（可等待或不等）
make ft-run
# 或
make ft-run-nowait

# 3) 查詢模型 tuning 狀態
make ft-status JOB=ftjob_XXXXXXXXXXXX

# 4) 測試訓練出來的模型
make ft-test

# 5) 把訓練好的模型存進去 registry 備用
MODEL_ID='${MODEL_ID}'
curl -sX POST http://localhost:8000/models/kb-assistant/versions \
  -H 'Content-Type: application/json' \
  -d "{
    \"version\": \"ft-2025-09-15\",
    \"artifact_url\": \"openai://models/${MODEL_ID}\",
    \"tags\": [\"kb\", \"ft\", \"openai\"],
    \"meta\": {
      \"artifact_type\": \"OpenAIFineTunedModel\",
      \"provider\": \"openai\",
      \"base_model\": \"gpt-4o-mini-2024-07-18\"
    }
  }" | jq

```
