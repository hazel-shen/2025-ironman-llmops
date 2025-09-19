# Day05 — Embedding 模型比較（OpenAI / HuggingFace MiniLM / BGE / Cohere）

本日目標：以四個最常見的 Embedding 選項做 **最小可執行 Demo**，直觀比較「請假 vs 休假」這種近義詞的相似度。

> 對應系列文章：Day05（Embedding 模型）、Day04（向量資料庫基礎）
>
> 💡 **延伸閱讀（成本）**：更多壓成本策略（Cache、Prompt 最小化、模型路由、長度控制），請見 **Day26**。

---

## 🧱 專案結構

```yaml
day05_embedding/
.
├── README.md
├── .env.example
├── bge_demo.py
├── cohere_demo.py
├── environment.yaml
├── huggingface_minilm_demo.py
└── openai_embedding_demo.py
```

## ⚙️ 快速開始

1. 建環境（conda）

```bash
conda env create -f environment.yaml
conda activate day05_embedding
```

2. 設定金鑰（可選）

複製 .env.example 為 .env，填入你要用到的 API key（OpenAI / Cohere 二選一或都填）：

```bash
cp .env.example .env
# 然後編輯 .env
```

.env.example 內容：

```dotenv
# 需要用到哪家就填哪家，沒填的 Demo 會略過或報錯（正常）
OPENAI_API_KEY=sk-...
COHERE_API_KEY=...
```

3. 執行四個 Demo

```bash
python openai_embedding_demo.py
# 期望輸出（示例）：
# 請假 vs 休假 相似度: 0.7618106440094277
# 休假 vs 旅行 相似度: 0.5885835750644238

python huggingface_minilm_demo.py

python bge_demo.py

python cohere_demo.py
```

## 💡 成本與效能提示

- API 成本量級：OpenAI text-embedding-3-small 約 $0.02 / 1M tokens；Cohere Embed v3 英文約 $0.10 / 1M tokens（實際以官網為準）。
- 維度影響儲存：OpenAI(1536) / MiniLM(384) / BGE(512) / Cohere(1024)。維度 ↑ → 向量儲存、索引成本 ↑。
- 批次處理：大量文件請用 batch（SentenceTransformer.encode(batch_size=XX) / API 批量）可顯著提升吞吐、降成本。
- 量化：大規模索引可考慮 int8/int4 量化以省 RAM（精度損失通常可接受）。

## 🐞 Troubleshooting

- HuggingFace 下載很慢：可先執行一次下載；或設定環境變數 `HF_HUB_ENABLE_HF_TRANSFER=1` 加速。
- BGE 相似度：若已 `normalize_embeddings=True`，`cosine` 就等於點積；別再除 `norm`。
- Cohere `input_type`：`search_document` 與 `search_query` 會產生不同向量；RAG 時兩端要一致。
- 中文字亂碼：確認檔案與終端機皆為 UTF-8。
- `Rate limit`：API 報 429 時加入簡單退避（exponential backoff）。
