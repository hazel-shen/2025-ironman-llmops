# Day13 — Data Drift 偵測 Demo

本資料夾展示三種 **知識庫變動偵測方法**，對應 2025 鐵人賽 Day13：

1. **Metadata 偵測**（檔案大小、修改時間、hash）
2. **版本號偵測**（文件內建版本號 / 發布日期）
3. **Embedding 語意差異比對**（文字語意是否有重要變動）

---

## 📦 環境安裝

使用 Conda 建立環境：

```bash
conda env create -f environment.yaml
conda activate day13_data_drift
```

若需要跑 **語意差異偵測**，請設定 OpenAI API Key：

```bash
export OPENAI_API_KEY=sk-xxxx
```

---

## 📂 專案結構

```bash
day13_data_drift/
├── README.md                  # 專案說明
├── environment.yaml           # Conda 環境設定
│
├── metadata_comparison.py     # 檔案 metadata 偵測
├── version_check.py           # 版本號偵測
├── embedding_comparison.py    # 語意差異偵測
│
├── faq_v1.yaml                # 測試 FAQ 舊版
├── faq_v2.yaml                # 測試 FAQ 新版
│
├── worker_manual.pdf          # 測試 PDF
└── worker_manual.meta.json    # PDF 的 metadata 紀錄
```

---

## ▶️ 使用方式

### 1. Metadata 偵測

比較檔案大小、修改時間與 hash：

```bash
python metadata_comparison.py
```

**範例輸出：**

```bash
# 把 Day12 的 worker_manual.pdf 移過來 Day13 用
❯ python metadata_comparison.py
📥 第一次建立 metadata 紀錄。

# 檔案沒有變動的情況下再執行一次
❯ python metadata_comparison.py
📂 檔案: worker_manual.pdf
  - 之前修改時間: 2025-09-27 11:17:25
  - 之前 Hash: 5106549b250c4c06a9bd1e59ab950e8a
  - 目前修改時間: 2025-09-27 11:17:25
  - 目前 Hash: 5106549b250c4c06a9bd1e59ab950e8a
✅ 檔案內容無變更。

# 修改 worker_manual.pdf 後儲存，再執行一次
❯ python metadata_comparison.py
📂 檔案: worker_manual.pdf
  - 之前修改時間: 2025-09-27 11:17:25
  - 之前 Hash: 5106549b250c4c06a9bd1e59ab950e8a
  - 目前修改時間: 2025-09-27 11:25:57
  - 目前 Hash: 0323bd12d945343f73035ab4503b2e3d
⚠️ 檔案內容已變更，需要更新知識庫！
```

### 2. 版本號偵測

比對 YAML 中的 version 欄位：

```bash
python version_check.py
```

**範例輸入：**

```yaml
# faq_v1.yaml
version: 1.0.0
faq:
  - q: 退貨政策
    a: 商品需在 7 天內退回
```

```yaml
# faq_v2.yaml
version: 1.1.0
faq:
  - q: 退貨政策
    a: 商品需在 14 天內退回
  - q: 是否支援線上客服？
    a: 是的，請至官網點選聊天室
```

**範例輸出：**

```bash
📋 版本比對結果
舊版本: 1.0.0
新版本: 1.1.0
🔄 偵測到版本更新，建議更新知識庫
```

### 3. 語意差異偵測

使用 OpenAI Embedding 判斷 FAQ 內容是否有語意上的重大差異：

```bash
python embedding_comparison.py
```

**範例輸出：**

```makefile
🧠 語意相似度分析
語意相似度: 0.9096
⚠️ 偵測到重要差異，需要更新知識庫！

詳細比對結果:
- 新增問題: "是否支援線上客服？"
- 修改內容: 退貨政策從 7 天改為 14 天
```

---

## 📝 注意事項

- `embedding_comparison.py` 需設定 `OPENAI_API_KEY` 才能運行
- **不適合用語意比對的場景**：程式碼、數據表格，請改用傳統 diff
- **建議用途**：法律條文、FAQ、SOP、政策文件等語意敏感的文本

---

## 🔧 進階配置

### 調整語意差異閾值

在 `embedding_comparison.py` 中修改：

```python
SIMILARITY_THRESHOLD = 0.95  # 預設值，可調整
```

### 自定義 Metadata 檢查項目

在 `metadata_comparison.py` 中可新增：

```python
def check_additional_metadata(filepath):
    # 新增檔案權限、擁有者等檢查
    pass
```

## 📊 效能參考

| 檔案大小 | Metadata 偵測 | 語意比對 |
| -------- | ------------- | -------- |
| < 1KB    | < 0.1s        | ~2s      |
| 1-10KB   | < 0.1s        | ~5s      |
| 10-100KB | < 0.5s        | ~15s     |

_語意比對時間依 OpenAI API 回應速度而定_
