# 🛡️ Day20 – 品質監控：幻覺偵測 (Hallucination Detection)

這個專案示範了三種常見的 LLM 幻覺檢查方法：

1. **Rule-based Check**

   - 利用正則、黑白名單、Schema 等規則，快速攔截明顯錯誤。
   - 範例：檢查 `/etc/` 系統路徑、缺少 URL、錯誤 JSON 格式。

2. **Retrieval-based Check**

   - 適用於 RAG 系統，檢查模型回答是否能在檢索片段中找到依據。
   - 範例：用 `sentence-transformers` 算語義相似度，低於閾值就標記為幻覺。

3. **LLM-as-a-judge**
   - 用另一個 LLM 當審核員，判斷回答是否忠於文件。
   - 適合抽樣檢查或高風險場景（醫療、金融）。

---

## 📂 專案結構

```yaml
day20-hallucination-detection/
├── environment.yml
├── README.md
├── rule_based_demo.py
├── retrieval_demo.py
└── llm_judge_demo.py
```

---

## 🚀 使用方式

### 1. 建立 conda 環境

```bash
conda env create -f environment.yaml
conda activate day20_quality_monitoring
```

2. 執行單一 Demo

```bash
python rule_based_demo.py
python retrieval_demo.py
python llm_judge_demo.py
```

---

📝 備註

Retrieval-based 使用 all-MiniLM-L6-v2 模型，適合快速 Demo。
Demo 3 - llm_judge_demo 需要 OpenAI 以及 Gemini 兩家的 API key，可在 .env 檔中放置：

```bash
OPENAI_API_KEY=sk-proj-XXX(你的 OpenAI API key)
GOOGLE_API_KEY=AI(你的 Gemini API key)
```
