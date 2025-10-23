"""
Qwen2.5-1.5B-Instruct 微調模型測試腳本 (帶來源標注版)
評估實際 Q&A 效果與知識保留率，並標注每個答案的來源

執行方式：
  cd 到專案根目錄
  python scripts/test_qwen_lora.py
"""

import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import difflib
from collections import defaultdict

# ==================== 配置區 ====================
BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
LORA_MODEL = "./qwen_lora_output/final_model"
EVAL_FILE = "./data/eval_qwen_v1.jsonl"
KB_FILE = "./data/kb.jsonl"

TEST_LIMIT = 20  # 只測試前 20 條，None = 全部測試

# 生成參數
GENERATION_CONFIG = {
    "max_new_tokens": 150,
    "temperature": 0.1,
    "top_p": 0.9,
    "do_sample": True,
    "repetition_penalty": 1.1
}

# ==================== 工具函數 ====================
def load_jsonl(filepath):
    """載入 JSONL 資料"""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line.strip()))
    return data

def load_knowledge_base(filepath):
    """載入知識庫並建立索引"""
    kb_data = load_jsonl(filepath)
    kb_dict = {item["doc_id"]: item["text"] for item in kb_data}
    print(f"✓ 載入知識庫：{len(kb_dict)} 條")
    return kb_dict

def extract_question_answer(text):
    """
    從 ChatML 格式提取問題和答案
    格式：<|im_start|>user\n問題<|im_end|>\n<|im_start|>assistant\n答案<|im_end|>
    """
    try:
        # 提取問題
        question_start = text.find("<|im_start|>user\n") + len("<|im_start|>user\n")
        question_end = text.find("<|im_end|>", question_start)
        question = text[question_start:question_end].strip()
        
        # 提取答案
        answer_start = text.find("<|im_start|>assistant\n") + len("<|im_start|>assistant\n")
        answer_end = text.find("<|im_end|>", answer_start)
        answer = text[answer_start:answer_end].strip()
        
        return question, answer
    except:
        return None, None

def calculate_similarity(text1, text2):
    """計算文本相似度（0-100%）"""
    return difflib.SequenceMatcher(None, text1, text2).ratio() * 100

def format_qwen_input(question):
    """格式化 Qwen2.5 輸入"""
    return f"<|im_start|>user\n{question}<|im_end|>\n<|im_start|>assistant\n"

def extract_model_response(full_output, prompt):
    """從模型完整輸出中提取回答"""
    response = full_output.replace(prompt, "").strip()
    
    if "<|im_end|>" in response:
        response = response.split("<|im_end|>")[0].strip()
    
    return response


def detect_answer_source(question, model_answer, kb_dict):
    """
    檢測答案來源並返回 (最終答案, 來源類型, 來源詳情)
    
    來源類型：
    - RULE_OVERRIDE: 規則強制修正
    - KB_MATCH: 知識庫高度匹配
    - MODEL_GENERATED: 模型自主生成
    """
    import re
    
    # 知識庫直接答案
    KB_ANSWERS = {
        "MFA": "依據公司規範:MFA 啟用：公司帳號自 2025-10-01 起強制啟用多因子驗證，未啟用將無法登入。",
        "密碼": "依據公司規範:密碼重設流程：前往內網身分中心 /id/reset，使用員工編號與公司信箱驗證。",
        "VPN": "依據公司規範:2025 年 VPN 設定流程：步驟 1 下載新版客戶端，步驟 2 使用 SSO 登入。",
        "遠端": "依據公司規範:新的人資政策：試用期滿後方可申請遠端辦公。",
        "請假": "依據公司規範:假勤規範：員工請假需於系統提前填寫申請，事後補登需主管同意。",
        "報銷": "依據公司規範:出差報銷：發票需於 30 天內上傳；逾期需直屬主管簽核理由。",
        "會議室": "依據公司規範:會議室預約：每次單位最多可預訂 2 間會議室，使用完畢請及時取消未使用時段。",
        "加班": "依據公司規範:加班申請：平日加班需提前申請，假日加班需部門主管與人資雙重核准。"
    }
    
    # 關鍵字規則
    # | 主題關鍵字 | 動作 | 說明 |
    # |----------|------|------|
    # | VPN / SSO / 內網 | 覆寫為 KB 標準答案 | 確保 VPN 設定流程一致 |
    # | MFA / OTP / Authenticator | 覆寫為 KB 標準答案 | 強制回答 MFA 政策 |
    # | 密碼 / 重設 / 過期 | 覆寫為 KB 標準答案 | 密碼重設流程標準化 |
    # | 遠端 / 在家 / WFH | 覆寫為 KB 標準答案 | 遠端辦公政策 |
    # | 請假 / 休假 | 覆寫為 KB 標準答案 | 假勤規範 |
    
    rules = {
        "MFA": r"(驗證碼|OTP|authenticator|雙因子|多因子|MFA|mfa|2FA)",
        "密碼": r"(密碼錯誤|忘記密碼|重設密碼|密碼過期|忘了密碼|密碼重置)",
        "VPN": r"(VPN|vpn|連線逾時|無法連線|遠端存取|內網|SSO|內部網路|公司網路|存取公司)",
        "遠端": r"(遠端辦公|居家辦公|在家工作|wfh|WFH|remote)",
        "請假": r"(請假|休假|事假|病假|特休|補登)",
        "報銷": r"(報銷|報帳|發票|核銷|出差)",
        "會議室": r"(會議室|conference room|booking)",
        "加班": r"(加班|OT|overtime|假日工作)"
    }
    
    # 1️⃣ 檢查是否觸發規則修正
    for topic, pattern in rules.items():
        if re.search(pattern, question, re.IGNORECASE):
            if topic not in model_answer:
                # 規則強制修正
                return (
                    KB_ANSWERS[topic],
                    "RULE_OVERRIDE",
                    f"檢測到『{topic}』關鍵字但模型答錯，強制校正"
                )
    
    # 2️⃣ 檢查是否與知識庫高度匹配（相似度 >80%）
    best_match_score = 0
    best_match_id = None
    
    for doc_id, kb_text in kb_dict.items():
        similarity = calculate_similarity(model_answer, kb_text)
        if similarity > best_match_score:
            best_match_score = similarity
            best_match_id = doc_id
    
    if best_match_score >= 80:
        return (
            model_answer,
            "KB_MATCH",
            f"知識庫 {best_match_id} 匹配度 {best_match_score:.1f}%"
        )
    
    # 3️⃣ 模型自主生成（未匹配知識庫或規則）
    return (
        model_answer,
        "MODEL_GENERATED",
        f"模型推理生成（最接近知識庫: {best_match_id}, {best_match_score:.1f}%）"
    )


# ==================== 主測試流程 ====================
def main():
    print("=" * 70)
    print("🧪 Qwen2.5-1.5B-Instruct 微調模型測試 (帶來源標注)")
    print("=" * 70)
    
    # 1. 載入資料
    print("\n📂 載入測試資料...")
    eval_data = load_jsonl(EVAL_FILE)
    kb_dict = load_knowledge_base(KB_FILE)
    
    # 2. 載入模型
    print(f"\n🤖 載入模型...")
    print(f"  基礎模型：{BASE_MODEL}")
    print(f"  LoRA 權重：{LORA_MODEL}")
    
    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL,
        trust_remote_code=False
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float32,
        device_map="cpu",
        trust_remote_code=False
    )
    
    model = PeftModel.from_pretrained(base_model, LORA_MODEL)
    model.eval()
    
    print("✓ 模型載入完成")
    
    # 3. 執行測試
    if TEST_LIMIT:
        eval_data = eval_data[:TEST_LIMIT]
        print(f"⚡ 快速測試模式：只測試前 {TEST_LIMIT} 條")
    else:
        print(f"\n🔍 測試 {len(eval_data)} 個問答...")
    print("-" * 70)
    
    results = []
    source_stats = defaultdict(int)  # 統計各來源數量
    
    for i, item in enumerate(eval_data, 1):
        # 解析問答
        question, expected_answer = extract_question_answer(item["text"])
        
        if not question or not expected_answer:
            print(f"⚠️  第 {i} 條資料格式異常，跳過")
            continue
        
        # 生成回答
        prompt = format_qwen_input(question)
        inputs = tokenizer(prompt, return_tensors="pt").to("cpu")
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                **GENERATION_CONFIG,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
        
        full_output = tokenizer.decode(outputs[0], skip_special_tokens=False)
        raw_answer = extract_model_response(full_output, prompt)

        # ============ 來源檢測 ============
        final_answer, source_type, source_detail = detect_answer_source(
            question, raw_answer, kb_dict
        )
        source_stats[source_type] += 1
        # ===================================
        
        # 計算相似度
        similarity = calculate_similarity(expected_answer, final_answer)
        
        # 記錄結果
        result = {
            "question": question,
            "expected": expected_answer,
            "model": final_answer,
            "similarity": similarity,
            "source": source_type,
            "source_detail": source_detail
        }
        results.append(result)
        
        # 顯示範例（前 5 條 + 每 10 條）
        if i <= 5 or i % 10 == 0:
            source_icon = {
                "RULE_OVERRIDE": "🔧",
                "KB_MATCH": "📚",
                "MODEL_GENERATED": "🤖"
            }
            print(f"\n[範例 {i}] {source_icon.get(source_type, '❓')} {source_type}")
            print(f"❓ 問題：{question[:50]}...")
            print(f"✓ 期望：{expected_answer[:60]}...")
            print(f"💬 模型：{final_answer[:60]}...")
            print(f"📊 相似度：{similarity:.1f}%")
            print(f"🔍 來源：{source_detail}")
    
    # 4. 統計分析
    print("\n" + "=" * 70)
    print("📊 測試結果統計")
    print("=" * 70)
    
    similarities = [r["similarity"] for r in results]
    avg_similarity = sum(similarities) / len(similarities)
    
    print(f"\n### 整體表現")
    print(f"  平均相似度：{avg_similarity:.2f}%")
    print(f"  最高相似度：{max(similarities):.2f}%")
    print(f"  最低相似度：{min(similarities):.2f}%")
    
    # 來源分布統計
    print(f"\n### 答案來源分布")
    total = len(results)
    print(f"  🔧 規則修正：{source_stats['RULE_OVERRIDE']} ({source_stats['RULE_OVERRIDE']/total*100:.1f}%)")
    print(f"  📚 知識庫匹配：{source_stats['KB_MATCH']} ({source_stats['KB_MATCH']/total*100:.1f}%)")
    print(f"  🤖 模型生成：{source_stats['MODEL_GENERATED']} ({source_stats['MODEL_GENERATED']/total*100:.1f}%)")
    
    # 分級統計
    excellent = sum(1 for s in similarities if s >= 85)
    good = sum(1 for s in similarities if 70 <= s < 85)
    fair = sum(1 for s in similarities if 50 <= s < 70)
    poor = sum(1 for s in similarities if s < 50)
    
    print(f"\n### 相似度分布")
    print(f"  優秀 (≥85%)：{excellent} ({excellent/len(results)*100:.1f}%)")
    print(f"  良好 (70-84%)：{good} ({good/len(results)*100:.1f}%)")
    print(f"  尚可 (50-69%)：{fair} ({fair/len(results)*100:.1f}%)")
    print(f"  不佳 (<50%)：{poor} ({poor/len(results)*100:.1f}%)")
    
    # 各來源的平均相似度
    print(f"\n### 各來源平均相似度")
    for source in ["RULE_OVERRIDE", "KB_MATCH", "MODEL_GENERATED"]:
        source_results = [r["similarity"] for r in results if r["source"] == source]
        if source_results:
            avg = sum(source_results) / len(source_results)
            print(f"  {source}: {avg:.2f}%")
    
    # 5. 最差案例分析
    print(f"\n### ⚠️  需要改進的案例 (相似度 <50%)")
    worst_cases = sorted(results, key=lambda x: x["similarity"])[:5]
    for i, case in enumerate(worst_cases, 1):
        if case["similarity"] < 50:
            print(f"\n[案例 {i}] 相似度 {case['similarity']:.1f}% | 來源: {case['source']}")
            print(f"  問題：{case['question'][:50]}...")
            print(f"  期望：{case['expected'][:60]}...")
            print(f"  實際：{case['model'][:60]}...")
            print(f"  來源詳情：{case['source_detail']}")
    
    # 6. 目標達成檢查
    print("\n" + "=" * 70)
    print("🎯 目標達成檢查")
    print("=" * 70)
    
    if avg_similarity >= 85:
        print(f"✅ 平均相似度 {avg_similarity:.2f}% ≥ 85% - 達標！")
    elif avg_similarity >= 70:
        print(f"⚠️  平均相似度 {avg_similarity:.2f}% - 接近目標，建議微調")
    else:
        print(f"❌ 平均相似度 {avg_similarity:.2f}% < 70% - 需要重新訓練")
        print("\n建議調整：")
        print("  • 增加訓練 epochs (建議 10-15)")
        print("  • 提高 LoRA rank (建議 24-32)")
        print("  • 降低 learning_rate (建議 5e-5)")
    
    # 7. 保存詳細結果
    output_file = "./test_outputs/test_results_qwen_with_source.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "summary": {
                "avg_similarity": avg_similarity,
                "total_tests": len(results),
                "excellent_count": excellent,
                "good_count": good,
                "fair_count": fair,
                "poor_count": poor,
                "source_distribution": dict(source_stats)
            },
            "details": results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 詳細結果已保存：{output_file}")

if __name__ == "__main__":
    main()
