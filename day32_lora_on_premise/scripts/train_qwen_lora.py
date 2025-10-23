"""
Qwen2.5-1.5B-Instruct LoRA 微調腳本 (M3 CPU 優化版)
針對企業 Q&A 知識庫優化
硬體：MacBook Air M3 24GB (CPU only)

執行方式：
  cd 到專案根目錄
  python scripts/train_qwen_lora.py
"""

import json
import torch
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model
import os
from datetime import datetime

# ==================== 配置區 ====================
MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
OUTPUT_DIR = "./qwen_lora_output"
TRAIN_FILE = "./data/train_qwen_final.jsonl" # 358
# TRAIN_FILE = "./data/train_qwen_v1.jsonl"
EVAL_FILE = "./data/eval_qwen_v1.jsonl"

# LoRA 配置
LORA_CONFIG = {
    "r": 16,
    "lora_alpha": 32,
    "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
    "lora_dropout": 0.05,
    "bias": "none",
    "task_type": "CAUSAL_LM"
}

# 訓練超參數（M3 CPU 優化）
TRAINING_CONFIG = {
    "learning_rate": 3e-4,           # 更高學習率快速收斂 (day32 版本：3e-4 / 最終調整：2e-4)
    "num_train_epochs": 3,           # 只要 3 個 epochs (day32 版本：3 / 最終調整：4)
    "per_device_train_batch_size": 4, # 增大 batch size
    "per_device_eval_batch_size": 4,
    "gradient_accumulation_steps": 2,
    "warmup_steps": 10,              # 最小 warmup (day32 版本：10 / 最終調整：30)
    "logging_steps": 5,
    "eval_strategy": "epoch",        # 改成每個 epoch 評估一次
    "save_strategy": "epoch",        # 每個 epoch 保存一次
    "max_grad_norm": 1.0,
    "lr_scheduler_type": "cosine",
    "weight_decay": 0.01,
    "fp16": False,
    "bf16": False,
    "save_total_limit": 1,
    "load_best_model_at_end": True,
    "metric_for_best_model": "eval_loss",
    "greater_is_better": False,
    "dataloader_num_workers": 0,
}

MAX_LENGTH = 192 # 要根據問答的 token 長度調整

# ==================== 資料處理 ====================
def load_jsonl(filepath):
    """載入 JSONL 格式資料"""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line.strip())
            data.append(item)
    print(f"✓ 載入 {len(data)} 筆資料：{filepath}")
    return data

def preprocess_data(examples, tokenizer):
    """批次處理資料"""
    tokenized = tokenizer(
        examples["text"],
        truncation=True,
        max_length=MAX_LENGTH,
        padding="max_length",
        return_tensors="pt"
    )
    
    tokenized["labels"] = tokenized["input_ids"].clone()
    return tokenized

# ==================== 主訓練流程 ====================
def main():
    print("=" * 60)
    print("🚀 Qwen2.5-1.5B LoRA 微調 (M3 CPU)")
    print("=" * 60)
    
    # 1. 載入資料
    print("\n📂 載入資料集...")
    train_data = load_jsonl(TRAIN_FILE)
    eval_data = load_jsonl(EVAL_FILE)
    
    train_dataset = Dataset.from_dict({"text": [item["text"] for item in train_data]})
    eval_dataset = Dataset.from_dict({"text": [item["text"] for item in eval_data]})
    
    print(f"✓ 訓練集：{len(train_dataset)} 筆")
    print(f"✓ 評估集：{len(eval_dataset)} 筆")
    
    # 2. 載入模型與 tokenizer
    print(f"\n🤖 載入模型：{MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        trust_remote_code=False,
        padding_side="right"
    )
    
    # 如果沒有 pad_token，就用 eos_token 代替：pad_token 告訴模型「這是填充物，不要學習」
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float32,
        device_map="cpu",
        trust_remote_code=False
    )
    
    print("✓ 模型載入完成")
    
    # 3. 配置 LoRA（移除 prepare_model_for_kbit_training）
    print("\n⚙️ 配置 LoRA...")
    lora_config = LoraConfig(**LORA_CONFIG)
    model = get_peft_model(model, lora_config)
    
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"✓ 可訓練參數：{trainable_params:,} / {total_params:,} "
          f"({100 * trainable_params / total_params:.2f}%)")
    
    # 4. 預處理資料
    print("\n📝 預處理資料...")
    train_dataset = train_dataset.map(
        lambda x: preprocess_data(x, tokenizer),
        batched=True,
        remove_columns=["text"]
    )
    eval_dataset = eval_dataset.map(
        lambda x: preprocess_data(x, tokenizer),
        batched=True,
        remove_columns=["text"]
    )
    
    # 5. 訓練配置
    print("\n⚙️ 初始化訓練器...")
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        overwrite_output_dir=True,
        **TRAINING_CONFIG,
        report_to=[]
    )
    
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=data_collator,
    )
    
    # 6. 開始訓練
    print("\n🔥 開始訓練...")
    total_steps = len(train_dataset) // (TRAINING_CONFIG['per_device_train_batch_size'] * TRAINING_CONFIG['gradient_accumulation_steps']) * TRAINING_CONFIG['num_train_epochs']
    print(f"預計總步數：{total_steps}")
    print(f"評估策略：{TRAINING_CONFIG['eval_strategy']}")  # ✅ 動態顯示
    print(f"⚠️  M3 CPU 訓練預估時間：35-45 分鐘")
    print(f"⏰ 開始時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = datetime.now()
    trainer.train()
    end_time = datetime.now()
    
    # 7. 保存模型
    print("\n💾 保存最終模型...")
    final_dir = os.path.join(OUTPUT_DIR, "final_model")
    trainer.save_model(final_dir)
    tokenizer.save_pretrained(final_dir)
    
    # 8. 訓練總結
    print("\n" + "=" * 60)
    print("✅ 訓練完成！")
    print("=" * 60)
    print(f"⏱️  訓練時間：{end_time - start_time}")
    print(f"📁 模型位置：{final_dir}")
    print(f"📊 最佳 checkpoint：{trainer.state.best_model_checkpoint}")
    print(f"📉 最佳 eval_loss：{trainer.state.best_metric:.4f}")
    
    # 9. 最終評估
    print("\n📊 執行最終評估...")
    eval_results = trainer.evaluate()
    print("評估指標：")
    for key, value in eval_results.items():
        print(f"  {key}: {value:.4f}")
    
    print("\n🎯 目標檢查：")
    final_loss = eval_results["eval_loss"]
    if final_loss < 0.6:
        print(f"  ✅ Eval loss {final_loss:.4f} < 0.6 - 達標！")
    else:
        print(f"  ⚠️  Eval loss {final_loss:.4f} >= 0.6 - 建議繼續訓練")
    
    print("\n💡 下一步：執行 python scripts/test_qwen_lora.py 測試實際效果")

if __name__ == "__main__":
    main()