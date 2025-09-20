# Day06 - Minimal RAG QA Demo

本專案展示了最小可行的 RAG (Retrieval-Augmented Generation) QA Bot。
透過 OpenAI Embedding API + FAISS 向量資料庫，實作一個可以回答「企業 FAQ」的簡單範例。

## 📦 專案結構

```yaml
day06_rag_mini/
.
├── README.md                # 專案說明文件，介紹 Demo 流程與使用方式
├── environment.yaml         # Conda 環境設定檔，安裝依賴套件
│
├── data/                    # 存放原始文件（知識庫）
│   └── docs.json            # (自動產生) 範例 FAQ 文件 (由 step1_prepare_docs.py 產生)
│
├── index/                   # 向量索引存放位置
│   ├── faiss.index          # (自動產生) FAISS 向量索引檔 (由 step2_build_index.py 產生)
│   └── meta.json            # (自動產生) 索引中繼資料（模型名稱、維度、文件清單）
│
├── step1_prepare_docs.py    # Step 1：建立知識文件 (輸出 data/docs.json)
├── step2_build_index.py     # Step 2：將文件轉換為向量並建立 FAISS 索引
├── step3_query_answer.py    # Step 3：檢索 + Augment + LLM 生成答案
└── utils_openai.py          # OpenAI 工具模組（Embedding + Chat 封裝）
```

## 🚀 環境安裝

建立 Conda 環境並安裝套件：

```bash
conda env create -f environment.yaml
conda activate day06_rag_mini

# 建立 .env 檔案，設定你的 OpenAI API Key：
echo "OPENAI_API_KEY=sk-xxxxxx" > .env
```

## 🛠️ 使用步驟

Step 1：建立文件

```bash
python step1_prepare_docs.py

# 輸出：
✅ 已寫入 data/docs.json
```

Step 2：建立索引

```bash
python step2_build_index.py
```

輸出檔案：

- index/faiss.index (向量索引檔)
- index/meta.json (索引中繼資料：模型、維度、文件數)

```bash
# 輸出：
✅ 建索引完成：3 篇，維度 1536
```

Step 3：查詢與生成答案

```bash
python step3_query_answer.py


# 範例輸出：
🔎 最相關文件： 請假流程：需要先主管簽核，然後到 HR 系統提交。

===== System Prompt =====
你是一個企業 FAQ 助理。請根據提供的知識庫內容回答使用者問題，若知識庫未涵蓋請說明不知道。

===== User Prompt =====
根據以下知識庫內容回答：
請假流程：需要先主管簽核，然後到 HR 系統提交。

問題：我要怎麼請假？

🧠 答案： 請假流程是需要先獲得主管的簽核，然後再到 HR 系統提交請假申請。
```

## ⚠️ 注意事項

1. 文件覆蓋

- 每次執行 `step1_prepare_docs.py` 都會重新產生 `data/docs.json`，舊版本會被覆蓋。
- 如果要保留之前的文件，請先手動備份。

2. 索引需重建

若修改了 `docs.json`，必須重新執行 `step2_build_index.py`，才能讓檢索反映最新文件。

3. API 成本

- Demo 使用 `OpenAI Embedding API` 和 `Chat API`，每次執行都會產生 Token 花費（通常很低，但仍需注意）。
- 若要避免 API 成本，可考慮改用本機 Embedding 模型（Day05 會比較不同方案）。

4. 環境需求

- 本專案預設使用 `Conda` 管理環境。若使用其他虛擬環境（venv、pipenv、poetry），需自行轉換 `environment.yaml`。
