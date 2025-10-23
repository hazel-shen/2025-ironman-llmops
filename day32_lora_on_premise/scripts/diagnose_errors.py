"""
診斷 Qwen 模型在哪些問題上答錯（評估集 85 條全部跑過一輪）
找出混淆的主題模式
v2: 加入進度條 + 修正警告
"""

import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
from difflib import SequenceMatcher
from tqdm import tqdm  # 進度條

# 配置
MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
LORA_MODEL_PATH = "./qwen_lora_output/final_model"
EVAL_FILE = "./data/eval_qwen_v1.jsonl"

def load_model():
    """載入微調後的模型"""
    print("🤖 載入模型...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=False)
    
    # 設定 pad_token
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    base_model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float32,
        device_map="cpu"
    )
    model = PeftModel.from_pretrained(base_model, LORA_MODEL_PATH)
    model.eval()
    print("✓ 模型載入完成\n")
    return model, tokenizer

def extract_answer(text):
    """提取 assistant 的回答部分"""
    if "<|im_start|>assistant" in text:
        answer = text.split("<|im_start|>assistant\n")[1].split("<|im_end|>")[0]
        return answer.strip()
    return text

def calculate_similarity(text1, text2):
    """計算兩段文字的相似度"""
    return SequenceMatcher(None, text1, text2).ratio()

def test_model(model, tokenizer, test_data):
    """測試模型並分析錯誤"""
    errors = []
    correct = []
    
    # 使用 tqdm 顯示進度條
    for idx, item in enumerate(tqdm(test_data, desc="🧪 測試進度", unit="題")):
        full_text = item["text"]
        
        # 提取問題和正確答案
        try:
            user_question = full_text.split("<|im_start|>user\n")[1].split("<|im_end|>")[0]
            correct_answer = extract_answer(full_text)
        except IndexError:
            print(f"⚠️  樣本 {idx+1} 格式錯誤，跳過")
            continue
        
        # 構建測試 prompt
        test_prompt = f"<|im_start|>user\n{user_question}<|im_end|>\n<|im_start|>assistant\n"
        
        # 生成回答（修正警告）
        inputs = tokenizer(test_prompt, return_tensors="pt")
        
        with torch.no_grad():  # 節省記憶體
            outputs = model.generate(
                **inputs,
                max_new_tokens=150,
                do_sample=False,
                temperature=None,      # 移除 temperature
                top_p=None,           # 移除 top_p
                top_k=None,           # 移除 top_k
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=False)
        model_answer = extract_answer(generated_text)
        
        # 計算相似度
        similarity = calculate_similarity(correct_answer, model_answer)
        
        result = {
            "idx": idx + 1,
            "question": user_question,
            "correct_answer": correct_answer,
            "model_answer": model_answer,
            "similarity": similarity * 100
        }
        
        if similarity < 0.9:  # 相似度 < 90% 視為錯誤
            errors.append(result)
        else:
            correct.append(result)
    
    return errors, correct

def analyze_errors(errors, correct):
    """分析錯誤模式"""
    print("\n" + "=" * 60)
    print("📊 測試結果總覽")
    print("=" * 60)
    
    total = len(errors) + len(correct)
    print(f"✅ 正確：{len(correct)} / {total} ({len(correct)/total*100:.1f}%)")
    print(f"❌ 錯誤：{len(errors)} / {total} ({len(errors)/total*100:.1f}%)")
    
    if not errors:
        print("\n🎉 所有測試都通過了！")
        return {}
    
    print("\n" + "=" * 60)
    print("❌ 錯誤答案詳細分析")
    print("=" * 60)
    
    # 按主題分類錯誤
    topic_patterns = {
        "登入/帳號": ["登入", "帳號", "mfa", "密碼", "雙因子", "驗證", "登不進"],
        "VPN/網路": ["vpn", "連線", "網路", "sso", "內網", "遠端"],
        "檔案/雲端": ["檔案", "雲端", "存放", "上傳", "分享"],
        "請假/加班": ["請假", "加班", "假單", "補登"],
        "報銷/差旅": ["報銷", "發票", "出差", "差旅", "升等"],
        "會議室": ["會議室", "預約", "訂"],
        "裝置/MDM": ["mdm", "磁碟", "加密", "筆電", "裝置"],
    }
    
    topic_errors = {topic: [] for topic in topic_patterns.keys()}
    topic_errors["其他"] = []
    
    for error in errors:
        question = error["question"].lower()
        correct = error["correct_answer"].lower()
        
        # 判斷屬於哪個主題
        matched_topic = "其他"
        for topic, keywords in topic_patterns.items():
            if any(kw in question or kw in correct for kw in keywords):
                matched_topic = topic
                break
        
        topic_errors[matched_topic].append(error)
    
    # 輸出分析結果
    for topic, errs in topic_errors.items():
        if errs:
            print(f"\n### 📌 主題：{topic} ({len(errs)} 個錯誤)")
            for err in errs[:5]:  # 只顯示前 5 個
                print(f"\n問題 {err['idx']}: {err['question']}")
                print(f"  ✓ 正確答案: {err['correct_answer'][:60]}...")
                print(f"  ✗ 模型答案: {err['model_answer'][:60]}...")
                print(f"  📊 相似度: {err['similarity']:.1f}%")
            
            if len(errs) > 5:
                print(f"  ... 還有 {len(errs)-5} 個錯誤")
    
    return topic_errors

def generate_confusion_matrix(errors):
    """生成混淆矩陣（哪個主題被誤判成哪個）"""
    print("\n" + "=" * 60)
    print("🔀 混淆模式分析")
    print("=" * 60)
    
    # 定義主題關鍵字
    topics = {
        "VPN": ["vpn", "連線", "sso"],
        "MFA": ["mfa", "雙因子", "多因子", "驗證", "2025-10-01"],
        "密碼": ["密碼", "重設", "/id/reset", "員工編號"],
        "報銷": ["報銷", "發票", "30 天"],
        "遠端": ["遠端", "居家", "wfh", "試用期"],
    }
    
    confusion = {}
    
    for error in errors:
        correct_ans = error["correct_answer"]
        model_ans = error["model_answer"]
        
        # 判斷正確答案屬於哪個主題
        correct_topic = "其他"
        for topic, keywords in topics.items():
            if any(kw in correct_ans.lower() for kw in keywords):
                correct_topic = topic
                break
        
        # 判斷模型答案屬於哪個主題
        model_topic = "其他"
        for topic, keywords in topics.items():
            if any(kw in model_ans.lower() for kw in keywords):
                model_topic = topic
                break
        
        # 記錄混淆
        if correct_topic != model_topic:
            key = f"{correct_topic} → {model_topic}"
            if key not in confusion:
                confusion[key] = []
            confusion[key].append(error)
    
    if confusion:
        print("\n常見的混淆類型：")
        for pattern, errs in sorted(confusion.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"  • {pattern}: {len(errs)} 次")
            if len(errs) > 0:
                print(f"    範例問題：{errs[0]['question']}")
    else:
        print("未發現明顯的混淆模式")

def main():
    # 載入評估資料
    with open(EVAL_FILE, 'r', encoding='utf-8') as f:
        eval_data = [json.loads(line) for line in f]
    
    print(f"📂 載入評估資料：{len(eval_data)} 筆\n")
    
    # 載入模型
    model, tokenizer = load_model()
    
    # 測試模型
    errors, correct = test_model(model, tokenizer, eval_data)
    
    # 分析錯誤
    topic_errors = analyze_errors(errors, correct)
    
    # 混淆矩陣
    if errors:
        generate_confusion_matrix(errors)
    
    # 保存結果
    output = {
        "total": len(eval_data),
        "correct": len(correct),
        "errors": len(errors),
        "error_rate": len(errors) / len(eval_data),
        "accuracy": len(correct) / len(eval_data),
        "detailed_errors": errors,
        "detailed_correct": correct[:10],  # 只保存前 10 個正確答案
        "topic_errors": {k: len(v) for k, v in topic_errors.items() if v}
    }
    
    with open("error_analysis.json", 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print("✅ 分析完成！")
    print("=" * 60)
    print(f"📊 正確率：{len(correct) / len(eval_data) * 100:.1f}%")
    print(f"📁 詳細報告已保存至：error_analysis.json")
    
    # 給出建議
    if len(errors) > 0:
        print("\n💡 改善建議：")
        if any("登入" in k or "帳號" in k for k in topic_errors.keys()):
            print("  • 登入/帳號相關主題混淆嚴重，建議增加區分性樣本")
        if len(errors) / len(eval_data) > 0.3:
            print("  • 錯誤率 >30%，建議執行 enhance_data.py 增強訓練資料")
        elif len(errors) / len(eval_data) > 0.15:
            print("  • 錯誤率 15-30%，可考慮微調超參數或小幅增加資料")
        else:
            print("  • 錯誤率 <15%，模型已相當不錯！")

if __name__ == "__main__":
    main()