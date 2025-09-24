# Day10 - Retriever + Reranker Demo

本日目標：  
展示 **Retriever (FAISS)** 與 **Reranker (Cross-Encoder)** 的二段式查詢流程。

---

## 📂 專案結構

```yaml
day10_retriever_and_reranker/
├── retriever_faiss_demo.py         # Retriever Demo：建立向量索引、輸出候選清單
├── reranker_cross_encoder_demo.py  # Reranker Demo：讀取候選清單並重新排序
├── compare_rerankers.py            # 額外比較三種 Reranker 模型
├── candidates.json                 # Retriever 輸出（Top-K 候選文件）
├── reranked.json                   # Reranker 輸出（精排後結果）
├── environment.yaml                # Conda 環境設定
└── README.md                       # 本說明文件
```

---

## 🚀 建立環境

```bash
conda env create -f environment.yaml
conda activate day10_retriever_and_reranker
```

---

## ▶️ 執行範例

本次 Demo 的查詢為：

**Query**：「公司的總部在哪裡？」  
**正確答案**：「本公司總部位於台北市信義區松高路 11 號。」

### 1. Retriever (FAISS)

快速找到候選文件並輸出至 `candidates.json`：

```bash
python retriever_faiss_demo.py
```

輸出範例：

```
=== 檢索器 (Retriever) Top-K 結果（未重排）===
[R01] 分數=0.8457 | idx=0 | 本公司總部位於台北市信義區松高路 11 號。
[R02] 分數=0.8144 | idx=1 | 公司創立於 2012 年，專注雲端與資料服務。
...
已輸出候選結果到 candidates.json
```

### 2. Reranker (Cross-Encoder)

讀取 `candidates.json`，使用 HuggingFace Cross-Encoder 進行精排，輸出 `reranked.json`：

```bash
python reranker_cross_encoder_demo.py
```

輸出範例：

```
=== 重排序器 (Reranker) Top-3 ===
[R*01] re=0.98 | ret=0.8457 | idx=0 | 本公司總部位於台北市信義區松高路 11 號。
...
已輸出重排結果到 reranked.json
```

### 3. 模型比較 (Compare Rerankers)

額外提供 `compare_rerankers.py`，可一次比較多種 Reranker 的行為與延遲。

```bash
python compare_rerankers.py
```

輸出範例：

```bash
查詢: 公司的總部在哪裡？

=== BAAI/bge-reranker-v2-m3 ===
Top1: 本公司總部位於台北市信義區松高路 11 號。 (score=0.9727)
Top2: 總部附近有一間 Starbucks 咖啡廳，常有員工聚會。 (score=0.0096)
Top3: 公司每年會在台北 101 舉辦年會。 (score=0.0065)
耗時: 1.94 秒

=== cross-encoder/ms-marco-MiniLM-L-12-v2 ===
Top1: 本公司總部位於台北市信義區松高路 11 號。 (score=0.9996)
Top2: 公司創立於 2012 年，專注雲端與資料服務。 (score=0.9993)
Top3: 我們在新加坡、東京與舊金山設有分公司據點。 (score=0.9993)
耗時: 0.18 秒

=== OpenAI GPT-4o-mini ===
Top1: 本公司總部位於台北市信義區松高路 11 號。 (score=5.00)
Top2: 公司每年會在台北 101 舉辦年會。 (score=3.00)
Top3: 我們在新加坡、東京與舊金山設有分公司據點。 (score=2.00)
耗時: 13.42 秒
```

---

## 📊 成品檔案

- **candidates.json**：Retriever 輸出的候選文件清單 (Top-K)。
- **reranked.json**：Reranker 輸出的精排結果 (Top-N)。

---

## 📝 注意事項

- `cross-encoder/ms-marco-MiniLM-L-6-v2` 模型主要在英文語料上訓練，中文效果有限，建議也可測試：

  - `BAAI/bge-reranker-base`
  - `BAAI/bge-reranker-v2-m3`（多語版）

- 如果出現 NaN 分數，可以改用 `sentence-transformers.CrossEncoder`，或在程式中加上 `torch.nan_to_num`。

---

## 🔗 延伸閱讀

- [Sentence-Transformers 官方文件](https://www.sbert.net/)
- [HuggingFace Cross-Encoder Models](https://huggingface.co/cross-encoder)
- [FAISS: Facebook AI Similarity Search](https://github.com/facebookresearch/faiss)
