# Day08 - 文件清洗與切片 (Cleaning & Chunking)

本日目標：  
將原始文件 (Word / PDF / HTML / Markdown) 經過 **清洗**與**切片 (Chunking)**，轉換成乾淨、結構化、容易檢索的片段，為後續 **向量化 (Embedding)** 與 **RAG 檢索**做準備。

---

## 🚀 環境安裝

使用 Conda：

```bash
conda env create -f environment.yaml
conda activate day08_cleaning_and_chunking
```

或使用 pip：

```bash
pip install -r requirements.txt
```

## 📂 專案結構

```
day08_cleaning_and_chunking/
├── cleaning_demo.py              # 文件清洗範例 (HTML → 乾淨段落)
├── fix_size_chunking.py          # 固定長度切片
├── sentence_base_chunking.py     # 句子切片
├── semantic_chunking.py          # 語意切片
├── environment.yaml              # Conda 環境設定檔
├── requirements.txt              # pip 需求檔
└── README.md                     # 說明文件
```

## 🧩 功能說明

### 1. 文件清洗 (cleaning_demo.py)

**處理步驟：**

- **去雜訊**：移除 HTML 標籤 (`nav/aside/footer/script/style` 等)、廣告、目錄。
- **正規化**：Unicode NFKC、空白折疊、標點簡化、數字單位轉換（10K → 10,000）。
- **結構保留**：保留 Markdown 標題、清單、程式碼區塊，避免語意破壞。
- **語言過濾**：僅保留指定語言（預設 zh / en）。
- **去重與過短過濾**：刪除重複段落，丟棄訊息量過低的片段。

**執行範例：**

```bash
python cleaning_demo.py
```

輸出：乾淨的段落清單，可直接送入後續 Chunking / Embedding。

### 2. 固定長度切片 (fix_size_chunking.py)

- 以 **固定長度 (N tokens/字元)** 進行切片。
- 可設定 **overlap**，避免跨區句子語意斷裂。

**執行範例：**

```bash
python fix_size_chunking.py
```

### 3. 句子切片 (sentence_base_chunking.py)

- 依據 **標點符號 (。？！；\n)** 進行切片。
- 更符合語意，自然適合 FAQ 或政策文件。

**執行範例：**

```bash
python sentence_base_chunking.py
```

### 4. 語意切片 (semantic_chunking.py)

- 利用 **關鍵詞/Embedding 相似度** 區分不同主題區塊。
- 能保持語意連貫，避免語境斷裂，但成本較高。

**執行範例：**

```bash
python semantic_chunking.py
```

## 📊 三種切片策略比較

| 策略         | 優點                     | 缺點                     | 適用場景                |
| ------------ | ------------------------ | ------------------------ | ----------------------- |
| 固定長度切片 | 實作簡單、速度快         | 可能切壞語意，片段不自然 | Demo、小規模測試        |
| 句子切片     | 語意自然、易懂           | 句子長度不一，可能過長   | FAQ、政策文件、說明文件 |
| 語意切片     | 語意連貫、能跨句聚合主題 | 成本高、需 Embedding     | 複雜文件、大型知識庫    |
