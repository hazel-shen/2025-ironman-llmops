# Day11 — Context Assembly Demos

本專案示範四種 **上下文組裝** 策略，並提供最小可跑的範例腳本：

```
./
├── README.md
├── environment.yaml
├── reranked.json                # Day10 輸出（作為本日輸入）
├── concatenation_demo.py
├── sliding_window_demo.py
├── chunk_ranking_demo.py
└── summarization_demo.py
```

## 1. 安裝環境

```bash
conda env create -f environment.yaml
conda activate day11_context_assembly
```

若你使用 mamba：

```bash
mamba env create -f environment.yaml
mamba activate day11_context_assembly
```

## 2. 輸入資料 (reranked.json)

本日範例會讀取 Day10 的輸出 `reranked.json`。最小結構如下（可依實際情況擴充）：

```json
{
  "query": "公司的總部在哪裡？",
  "reranked": [
    {
      "idx": 0,
      "title": "公司簡介",
      "source": "about.md",
      "text": "本公司總部位於台北市信義區松高路 11 號。",
      "retriever_score": 0.8457,
      "reranker_score": 0.9123
    },
    {
      "idx": 1,
      "title": "歷史",
      "source": "history.pdf",
      "text": "公司創立於 2012 年，專注雲端與資料服務。",
      "retriever_score": 0.8144,
      "reranker_score": 0.8876
    }
  ]
}
```

### 欄位說明

- `query`：使用者查詢字串
- `reranked`：已重排序的候選文件（由高到低）
- `text`：片段內容（必要）
- `title` / `source`：可選，用於顯示/引用
- `retriever_score` / `reranker_score`：可選，用於觀測/除錯

## 3. 執行各策略 Demo

### 3.1 Concatenation（直接拼接）

```bash
python concatenation_demo.py
```

### 3.2 Sliding Window（片段擷取）

```bash
python sliding_window_demo.py
```

### 3.3 Chunk Ranking（切片後再排序取高分片段）

```bash
python chunk_ranking_demo.py
```

### 3.4 Summarization（先摘要再拼接）

```bash
python summarization_demo.py
```

**注意事項：**

- 第一次執行會自動下載模型（來自 Hugging Face Hub）
- 需要網路連線
- 預設快取路徑：`~/.cache/huggingface`（可透過 `HF_HOME` 調整）
- 若遇到 tokenizer 或 sentencepiece 錯誤，請確認已啟用此 Conda 環境

## 4. 平台與裝置小貼士

### Apple Silicon (M1/M2/M3)

安裝完本環境後，PyTorch 一般可直接使用 MPS。程式中可用：

```python
device = "mps" if torch.backends.mps.is_available() else "cpu"
model.to(device)
```

### NVIDIA CUDA（可選）

- 需以對應 CUDA 版本安裝 PyTorch（見 [PyTorch 官網](https://pytorch.org/)）
- 程式中使用 `device = "cuda" if torch.cuda.is_available() else "cpu"`

## 5. 常見問題（FAQ）

### Q: 匯入失敗：ModuleNotFoundError: No module named 'transformers'

**A:** 確認已 `conda activate day11_context_assembly`，且安裝 `environment.yaml` 成功。

### Q: 中文/多語模型無法 Tokenize

**A:** 請確認已安裝 `sentencepiece`（本環境已包含），或重新安裝後再試。

### Q: 下載模型很慢

**A:** 可設定環境變數：

```bash
export HF_HOME=~/.cache/hf
```

並確保網路可存取 `huggingface.co`。

### Q: Windows 終端機亂碼

**A:** 可改用 Windows Terminal 或先執行 `chcp 65001` 切 UTF-8。

## 6. 策略說明

### Concatenation（直接拼接）

將所有選中的文件片段直接串接，適合內容較短且相關性高的場景。

### Sliding Window（片段擷取）

使用滑動視窗技術，擷取最相關的文本片段，避免內容過長導致的效能問題。

### Chunk Ranking（切片後再排序）

先將文件切分成更小的片段，再次進行相關性排序，選取最相關的片段組合。

### Summarization（先摘要再拼接）

對每個文件片段進行摘要處理，再將摘要結果拼接，適合處理大量長文本的場景。

## 7. 輸出格式

所有 demo 腳本都會輸出：

- 原始查詢
- 選用的策略名稱
- 組裝後的上下文內容
- 處理統計資訊（如使用的片段數量、總字數等）
