# 🧪 Minimal RAG QA Bot Demo

這是一個最小可行的 **RAG QA Bot** Demo，包含：

- **後端**：FastAPI + FAISS + OpenAI API
- **前端**：純 HTML + Fetch API
- **知識庫**：10 條企業 FAQ（可自行擴充）

## 📁 專案結構

```yaml
day07_web_rag_mini
.
├── backend/
│   └── main.py         # FastAPI 主程式
├── frontend/
│   └── index.html      # 簡單前端頁面
├── environment.yml     # conda 環境設定
└── README.md
```

## 🔑 環境變數

請設定 OpenAI API Key：

```bash
export OPENAI_API_KEY=sk-xxxxxx
```

（Windows PowerShell 用 setx OPENAI_API_KEY sk-xxxxxx）

或是把 `OPENAI_API_KEY` 寫進去 `.env`

```bash
# 建立 .env 檔案，設定你的 OpenAI API Key：
echo "OPENAI_API_KEY=sk-xxxxxx" > .env
```

## 📦 安裝環境

建議使用 **conda**：

```bash
conda env create -f environment.yaml
conda activate day07_web_rag_mini
```

啟動服務

```bash
python backend/main.py
```

## 🌐 使用方式

啟動後，打開瀏覽器並輸入：

- http://127.0.0.1:8000/
- http://localhost:8000/

即可看到簡單的前端頁面，輸入問題與 Bot 互動 👌

## 🧪 測試問題範例

```yaml
- 我要怎麼報銷？
- VPN 怎麼用？
- 遲到會怎樣？
- 什麼時候要去健檢？
- 公司午餐補助多少？
```
