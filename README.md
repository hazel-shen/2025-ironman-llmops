# 2025-ironman-llmops

(🚧 每日更新中...)

本倉庫收錄了 2025 iThome 鐵人賽的相關內容與示範程式碼。  
主題圍繞 **LLMOps**，透過每日的文章與程式碼範例，逐步展現從零到一的完整實作歷程。
如有問題，歡迎直接開 issues 或是在文章底下留言友善交流。😊

## Articles & Links

| 日期       |                                                              文章                                                              |
| ---------- | :----------------------------------------------------------------------------------------------------------------------------: |
| 2025/09/15 |                 [Day01 - 為什麼需要 LLMOps？與傳統 MLOps 差異](https://ithelp.ithome.com.tw/articles/10380053)                 |
| 2025/09/16 |                 [Day02 - 系列專案介紹：企業知識庫 QA Chatbot](https://ithelp.ithome.com.tw/articles/10380054)                  |
| 2025/09/17 |                       [Day03 - 環境準備：Docker + Conda](https://ithelp.ithome.com.tw/articles/10381623)                       |
| 2025/09/18 |          [Day04 - 向量資料庫（Vector Database）- 常見選項與實務比較](https://ithelp.ithome.com.tw/articles/10382486)           |
| 2025/09/19 |         [Day05 - 向量模型（Embedding）- 四種 Embedding 模型實測與選型](https://ithelp.ithome.com.tw/articles/10383158)         |
| 2025/09/20 |              [Day06 - 初探 RAG（Retrieval-Augmented Generation）](https://ithelp.ithome.com.tw/articles/10384021)              |
| 2025/09/21 |                 [Day07 — 最小可行的 RAG QA Bot（Web 版 MVP）](https://ithelp.ithome.com.tw/articles/10384741)                  |
| 2025/09/22 |         [Day08 - 文件清洗 (Cleaning) 與切片策略 (Chunking Strategies)](https://ithelp.ithome.com.tw/articles/10385277)         |
| 2025/09/23 |               [Day09 - 向量化 （Vectorize）與索引（Index）建立](https://ithelp.ithome.com.tw/articles/10386191)                |
| 2025/09/24 |            [Day10 - RAG 查詢實作：Retriever ＋ Reranker 與模型評測](https://ithelp.ithome.com.tw/articles/10386952)            |
| 2025/09/25 | [Day11 - 上下文組裝（Context Assembly）：實測四種策略，讓 LLM「讀得懂又省錢」](https://ithelp.ithome.com.tw/articles/10387588) |
| 2025/09/26 |             [Day12 - 知識庫資料管理：多來源整合 × 可追溯版本控制](https://ithelp.ithome.com.tw/articles/10388360)              |
| 2025/09/27 |         [Day13 - 為什麼知識會「過期」？Data Drift 偵測與更新策略實作](https://ithelp.ithome.com.tw/articles/10388907)          |
| 2025/09/28 | [Day14 - LLMOps Pipeline 自動化實戰：用 Prefect 與 Dagster，拯救你的睡眠時間](https://ithelp.ithome.com.tw/articles/10389635)  |
| 2025/09/29 |     [Day15 - Prompt Generation：用模板和版本管理 Prompt，規範 LLM 的回應](https://ithelp.ithome.com.tw/articles/10390630)      |
| 2025/09/30 |        [Day16 - LangChain × Guidance：打造可組合、可控的 Prompt 工作流](https://ithelp.ithome.com.tw/articles/10391276)        |
| 2025/10/01 |            [Day17 - 成本、隱私、維運怎麼取捨？LLM 應用部署策略解析](https://ithelp.ithome.com.tw/articles/10391897)            |
| 2025/10/02 |     [Day18 - 用 FastAPI 實作 LLM API Gateway：驗證、限流、觀測與實務選型](https://ithelp.ithome.com.tw/articles/10392318)      |
| 2025/10/03 |            [Day19 - 掌握 LLM 應用可觀測性：監控延遲、Token 與成本](https://ithelp.ithome.com.tw/articles/10392798)             |
| 2025/10/04 |               [Day20 - LLM 回應品質監控：幻覺偵測與三層防護實作](https://ithelp.ithome.com.tw/articles/10393293)               |

## ⚠️ 使用提醒

本系列文章與範例程式碼中，部分功能會用到 `OpenAI` API（如 `GPT-4o mini`、`GPT-4.1` 等）。
在實作或延伸應用時，請特別留意以下事項：

費用控制：不同模型的 API 價格差異很大。範例大多已做過「縮短 Prompt」、「選用較便宜模型」、「快取 Token」等優化。若您輸入大量資料或選擇高單價模型，費用可能會增加，請自行留意帳務。

模型替換：範例以 `OpenAI` API 為主，但您也可以依需求改用其他 LLM 服務商（如 `Anthropic`、`Cohere`、`Azure OpenAI` 等），只要 API 介面相容或稍作調整即可。

善用資源：本系列內容主要用於學習與研究。若在實務專案中導入，建議額外考量 隱私保護、資料安全、成本監控 等議題，確保系統符合您的需求。

🙏 希望這些內容能幫助您更順利地探索與實踐 `LLMOps`！
