# Prompt Chaining & Structured Output Demos

這個專案示範如何使用 **LangChain** 與 **Guidance** 來設計 Prompt Template、Chain 與格式控制。  
透過幾個簡單的範例程式，展示如何把 Prompt Registry (YAML) 結合 LLM，產生 FAQ 與摘要的工作流程。

---

## 📂 專案結構

```yaml
day16_prompt_templates
.
├── combined_demo.py              # LangChain + Guidance 混合範例
├── guidance_faq_json_demo.py     # 使用 Guidance 控制 JSON 格式輸出
├── langchain_chain_router_demo.py # 使用 LangChain 建立 Router Chain 範例
├── langchain_chain_demo.py       # 使用 LangChain 建立 Prompt Chain 範例
├── prompts/
│   ├── prompts_v1.yaml          # Prompt Registry v1 (summary / faq)
│   └── prompts_v2.yaml          # Prompt Registry v2 (可擴充)
└── requirements.txt              # 所需套件
```

---

## 📦 安裝環境

建議使用 **Python 3.11**，並建立虛擬環境：

### 使用 venv

```bash
# 建立環境
python -m venv .venv
source .venv/bin/activate

# 安裝依賴
pip install -r requirements.txt
```

### 使用 conda

```bash
# 建立 conda 環境
conda create -n day15_prompt_registry python=3.11 -y
conda activate day15_prompt_registry

# 安裝依賴
pip install -r requirements.txt
```

---

## 🔑 設定 API Key

建立 `.env` 檔，放置 OpenAI API Key：

```env
OPENAI_API_KEY=sk-xxxxxx
```

---

## 🚀 使用方式

### 1. LangChain Chain Demo

```bash
python langchain_chain_demo.py
```

**輸出包含：**

- **用法 A**：直接 QA（context + question → 答案）
- **用法 B**：先摘要再 QA（context → 摘要 → 問題 → 答案）

### 2. LangChain Router Demo

```bash
python langchain_chain_router_demo.py
```

**特色：**

使用 Router Chain 判斷問題類型並分流：

- 沒有問題 → 走 Summary
- 問題含價格關鍵詞 → 走 Pricing Prompt
- 其他 → 走 FAQ Prompt

適合 多場景分流 的應用，例如客服問答系統。

### 3. Guidance JSON FAQ Demo

```bash
python guidance_faq_json_demo.py
```

**特色：**

- 示範如何保證輸出符合 JSON 結構
- 適合需要**強制格式**的情境（API 回傳、前端結構化資料）

### 4. LangChain + Guidance 組合 Demo

```bash
python combined_demo.py
```

**架構優勢：**

- 用 **LangChain** 管理流程（多步驟 Chain）
- 用 **Guidance** 控制輸出格式（JSON/Markdown/Schema）

---

## 📘 Prompt Registry

Prompts 都集中在 `prompts/` 資料夾中，方便版本管理：

- **v1**：基本的 Summary 與 FAQ
- **v2**：可擴充設計，支援更多模板

---

## 🛠️ 技術特點

- **Prompt 版本控制**：使用 YAML 管理不同版本的 prompts
- **格式化輸出**：透過 Guidance 確保輸出符合預期格式
- **模組化設計**：Chain 可重複使用與組合
- **易於擴充**：新增 prompt 只需編輯 YAML 檔案

---

## ⚠️ 常見錯誤與處理方式

在實際執行 Demo 或建構應用時，常會遇到以下錯誤情境：

| 錯誤類型         | 建議處理方式                                                  |
| ---------------- | ------------------------------------------------------------- |
| **Timeout**      | 設定 Retry / Backoff 機制，避免立即重送造成壓力               |
| **格式解析失敗** | 改善 Parser 邏輯，或增加 fallback（例如回傳純文字而非 JSON）  |
| **Quota 超限**   | 快速偵測並回報錯誤訊息，避免浪費資源；建議搭配監控 API 使用量 |

---

## 📋 Requirements

主要依賴套件：

- `langchain`
- `guidance`
- `openai`
- `pyyaml`
- `python-dotenv`

詳細版本請參考 `requirements.txt`

> ⚠️ 版本相容性提醒
> LangChain 和 Guidance 生態更新速度快，常有破壞性改動。  
>  本文測試時的套件版本如下，建議依照此版本執行，若未來遇到 API mismatch，請先檢查套件版本是否不同：

```txt
# LangChain 生態
langchain>=0.2.11
langchain-core>=0.2.21
langchain-openai>=0.1.7

# Guidance
guidance>=0.1.14
```

---

## 💡 使用案例

1. **自動化客服系統**：使用 FAQ 模板產生結構化回答
2. **文件摘要服務**：批次處理長文件並產生重點摘要
3. **API 整合**：確保 LLM 輸出符合下游 API 格式要求
4. **內容生成管線**：串接多個 prompt 完成複雜任務
