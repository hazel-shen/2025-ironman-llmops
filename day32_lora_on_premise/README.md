# Day 32 - LoRA 自建再訓練 Demo (Qwen2.5)

📚 本專案為 2025 iThome 鐵人賽 - LLMOps 系列 Day 32 的完整程式碼

## 🎯 Demo 說明

本專案示範如何將 Day 23 的知識庫 (kb.jsonl) 轉換成訓練/驗證資料集，並利用 `LoRA (Low-Rank Adaptation)` 在本機 (Mac M3/CPU/GPU) 或 `Colab` 上對 `Qwen2.5-1.5B-Instruct` 進行輕量化微調，讓模型學會：

- ✅ 以企業語氣回答 FAQ
- ✅ 引用知識庫規範 (依據公司規範: ...)
- ✅ 沒有依據時禮貌拒答
- ✅ 搭配「規則後處理」提升準確率至 90%+

M3 約 40 分鐘即可完成，不需上傳資料到雲端。

## 📁 專案結構

```
day32_lora_on_premise/
├── data/
│   ├── kb.jsonl               # 知識庫 (Day 23 複製)
│   ├── train_qwen_v1.jsonl    # 訓練集 (由 KB 生成)
│   └── eval_qwen_v1.jsonl     # 驗證集 (泛化測試)
├── scripts/
│   ├── diagnose_errors.py          # (Optional) Day33 用的腳本，拿來跑過全部的驗證集，知道模型的弱點問句在哪
│   ├── fix_remaining_issues.py     # (Optional) Day33 用的腳本，拿來對症下藥，讓訓練集有更多精準的提問
│   ├── generate_qwen_train_set.py  # 步驟 1: 生成訓練集
│   ├── generate_qwen_eval_set.py   # 步驟 1: 生成驗證集
│   ├── train_qwen_lora.py          # 步驟 2: 執行 LoRA 微調
│   └── test_qwen_lora.py           # 步驟 3: 測試 + 後處理
├── environment.yaml           # Conda 環境
└── README.md
```

## 🚀 快速開始 (5 步驟)

### 步驟 0: 安裝環境

```bash
# Conda
conda env create -f environment.yaml
conda activate day32_lora_on_premise

# 或 pip
pip install torch transformers peft accelerate datasets safetensors
```

### 步驟 1: 準備資料

```bash
# 複製知識庫
cp ../day23_iteration/data/kb.jsonl data/

# 生成訓練/驗證集
python scripts/generate_qwen_train_set.py
python scripts/generate_qwen_eval_set.py
```

### 步驟 2: 訓練模型

```bash
python scripts/train_qwen_lora.py
# M3 24GB: 30-40 分鐘
# Colab T4: 8-12 分鐘
```

### 步驟 3: 測試效果

```bash
❯ python scripts/test_qwen_lora.py
======================================================================
🧪 Qwen2.5-1.5B-Instruct 微調模型測試 (帶來源標注)
======================================================================

📂 載入測試資料...
✓ 載入知識庫：15 條

🤖 載入模型...
  基礎模型：Qwen/Qwen2.5-1.5B-Instruct
  LoRA 權重：./qwen_lora_output/final_model
✓ 模型載入完成
⚡ 快速測試模式：只測試前 20 條
----------------------------------------------------------------------
Starting from v4.46, the `logits` model output will have the same type as the model (except at train time, where it will always be FP32)

[範例 1] 📚 KB_MATCH
❓ 問題：vpn 連線逾時...
✓ 期望：依據公司規範:2025 年 VPN 設定流程：步驟 1 下載新版客戶端，步驟 2 使用 SSO 登入。...
💬 模型：依據公司規範:2025 年 VPN 設定流程：步驟 1 下載新版客戶端，步驟 2 使用 SSO 登入。...
📊 相似度：100.0%
🔍 來源：知識庫 doc_611a2e74 匹配度 92.6%
```

### 步驟 4: (Optional) 註冊到 Registry

```bash
tar -czf qwen-lora-v1.tar.gz -C qwen_lora_output final_model/
```

## 📊 實驗成果

- 訓練集 299 筆 / 驗證集 85 筆
- 純模型平均相似度：78%
- 加上規則後處理：92%+
- 常見誤差：VPN vs MFA 混淆，冒號格式不一致、未知問題無法拒答，Day33 會解釋如何處理

## 🐛 常見問題

**Q: 記憶體不足?**  
降低 `per_device_train_batch_size`，或改用 Colab GPU。

## 📚 延伸閱讀

| Day    | 主題                                                                     | 解決問題            | 本篇整合         |
| ------ | ------------------------------------------------------------------------ | ------------------- | ---------------- |
| Day 20 | [品質監控](https://ithelp.ithome.com.tw/articles/10393293)               | 偵測幻覺            | ✅ 相似度驗證    |
| Day 22 | [Model Registry](https://ithelp.ithome.com.tw/articles/10394144)         | 版本管理            | ✅ LoRA 版本註冊 |
| Day 23 | [RAG 增量 × Fine-tuning](https://ithelp.ithome.com.tw/articles/10394515) | 知識更新 + 語氣統一 | ✅ 80% 場景方案  |
