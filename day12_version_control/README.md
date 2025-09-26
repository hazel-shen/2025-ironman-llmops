# Day12 - 知識庫資料管理：多來源整合 × 可追溯版本控制

本 repo 只放「可以跑的最小專案骨架」。  
原理解說、流程圖、實戰細節請看文章 Day12。

---

## 🔧 0) 需求

- **Conda**（Miniconda / Anaconda）
- **Git**（跑 DVC 流程需要）
- **AWS CLI**（_可選_：DVC remote 設 S3 時）

---

## 📦 1) 安裝

```bash
conda env create -f environment.yaml
conda activate day12_version_control
```

> 💡 若 lxml 安裝卡住，可先從 environment.yaml 移除它再建立環境。

---

## 📁 2) 目錄結構

```yaml
./day12_version_control
├── README.md                   # 精簡操作說明（不重複文章內容）
├── api_ingestion_demo.py       # Demo 3：API/JSON 匯入 → chunks/索引
├── environment.yaml            # Conda 環境定義（用 conda-forge 套件）
├── metadata.json               # 由 metadata_demo.py 產生的版本記錄（hash/timestamp）
├── metadata_demo.py            # 小型方案：Git + Metadata 版本控管示範
├── pdf_ingestion_demo.py       # Demo 1：PDF 匯入（含錯誤處理）→ chunks/索引/查詢
├── web_ingestion_demo.py       # Demo 2：Web/RSS 匯入 → 清洗/切片 → 索引/查詢
├── worker_manual.pdf           # 測試用 PDF（建議用 DVC 管理內容）
├── worker_manual.pdf.dvc       # DVC 指標檔（由 Git 追蹤，實體內容在 remote）
└── worker_manual.txt           # 測試用文字檔（給 metadata_demo.py 使用）
```

---

## 🚀 3) 快速執行

### 3.1 Ingestion Demos

```bash
# PDF
cd day12_ingestion
python pdf_ingestion_demo.py

# Web
python web_ingestion_demo.py   # 改成你可抓取的 URL

# API / JSON
python api_ingestion_demo.py
```

### 3.2 小型版本控管（Git + Metadata）

```bash
cd ../day12_version_control
python metadata_demo.py
cat metadata.json
```

### 3.3 中型版本控管（DVC + S3）

> ⚠️ 需先 `aws configure`，且有建立 bucket 權限。

```bash
# 專案根目錄
dvc init
dvc add day12_version_control/worker_manual.pdf
git add day12_version_control/worker_manual.pdf.dvc .dvc/ .gitignore
git commit -m "Track worker_manual.pdf with DVC"

# 設定 S3 remote（請替換名稱/區域）
aws s3 mb s3://your-dvc-demo-bucket --region ap-northeast-1
dvc remote add -d myremote s3://your-dvc-demo-bucket/dvc-store
dvc remote modify myremote region ap-northeast-1

# 上傳內容物到 S3
dvc push
```

**多人協作要檢查看看有沒有衝突**：

> 觀念：內容檔放 remote（S3/GCS），版本資訊跟著 Git（.dvc / dvc.lock）。衝突多發生在 Git 層 而非二進位內容本身。

```bash
# 0) 先跟上 Git（很關鍵）
git pull --rebase

# 1) 取得遠端資料狀態
dvc fetch
dvc status -r

# 2) 若同一檔案被多人改動 → Git 會出現衝突
#    手動解衝突 .dvc / dvc.lock 後，還原工件
dvc checkout

# 3) 確認可重現
dvc repro         # 需要時重算
dvc status

# 4) 同步到遠端
git add . && git commit -m "Resolve DVC conflict"
git push
dvc push
```

---

## ❓ 4) 常見問題（只列操作向）

- **`ModuleNotFoundError: pdfplumber`** → 先 `conda activate day12_version_control`，再執行；或 `conda install -c conda-forge pdfplumber`
- **PDF 無文字** → 可能是掃描檔，需 OCR（本 repo 不含）
- **DVC 取不到資料** → 先 `git pull --rebase`，再 `dvc fetch / dvc status -r` 檢查 remote 設定與 IAM 權限
