# Day13 Mini Pipeline — Data Drift Detection & Update

這是一個最小可跑的 **知識庫更新 Pipeline Demo**，展示如何拆分成 `steps/`，模擬真正的自動化任務流程（為 Day14 自動化鋪墊）。

---

## 📂 專案結構

```
day13_mini_pipeline/
├── data/
│   └── faq.txt                 # 自動產出：範例輸入文件
├── artifacts/
│   ├── vector_index.json       # 自動產出：向量索引
│   └── source.hash             # 自動產出：上次版本 Hash
├── steps/
│   ├── detect.py               # 偵測檔案是否變動
│   ├── embed.py                # 向量化 (local hashing / OpenAI)
│   └── update_index.py         # 更新索引
└── pipeline.py                 # 串接整個流程
```

---

## 🚀 使用方式

### 1. 建立 Conda 環境

```bash
conda env create -f environment.yaml
conda activate day13_mini_pipeline
```

### 2. 執行 Pipeline

```bash
python pipeline.py
```

- **第一次跑** → 會產生 `artifacts/vector_index.json` 與 `artifacts/source.hash`
- **第二次跑**（若檔案沒改變） → 會自動跳過更新
- **修改 `data/faq.txt` 後再跑** → 會重新更新索引

---

## ⚙️ OpenAI Embeddings（選用）

若你想用 OpenAI 取代 local hashing 向量化，設定以下環境變數：

```bash
export OPENAI_API_KEY=sk-xxxx
export USE_OPENAI=true
```

再執行：

```bash
python pipeline.py
```

---

## 📋 功能特色

- ✅ **Data Drift Detection** - 自動偵測檔案變更
- ✅ **步驟化架構** - 清晰的 Pipeline 流程
- ✅ **支援多種向量化方式** - Local Hashing 或 OpenAI Embeddings
- ✅ **增量更新** - 只在檔案變動時才重新處理
- ✅ **可擴展設計** - 為自動化部署做好準備

---

## 🔧 開發說明

### Pipeline 流程

1. **detect.py** - 計算檔案 Hash，比對是否有變動
2. **embed.py** - 將文件內容向量化（支援 Local/OpenAI 兩種模式）
3. **update_index.py** - 更新向量索引並儲存

### 環境變數

| 變數名           | 說明                       | 預設值  |
| ---------------- | -------------------------- | ------- |
| `USE_OPENAI`     | 是否使用 OpenAI Embeddings | `false` |
| `OPENAI_API_KEY` | OpenAI API 金鑰            | -       |

---

## 📝 範例輸出

```bash
❯ python pipeline.py
🔍 檢查檔案是否變動…
⚠️ 偵測到變動，開始更新索引…
✂️ 切出 2 個片段
🧠 使用 OpenAI Embeddings (text-embedding-3-small)
🧠 產生 2 筆向量
📦 已寫入索引：artifacts/vector_index.json
🎉 更新完成！


❯ python pipeline.py
🔍 檢查檔案是否變動…
✅ 無變動，跳過更新

❯ python pipeline.py
🔍 檢查檔案是否變動…
⚠️ 偵測到變動，開始更新索引…
✂️ 切出 3 個片段
📊 使用 Local Hashing Embeddings
🧠 產生 3 筆向量
📦 已寫入索引：artifacts/vector_index.json
🎉 更新完成！

❯ python pipeline.py
🔍 檢查檔案是否變動…
✅ 無變動，跳過更新
```
