"""
針對剩餘 26 個錯誤進行精準修復
新增 20 筆高品質樣本
"""

import json

KB = {
    "mfa": "MFA 啟用：公司帳號自 2025-10-01 起強制啟用多因子驗證，未啟用將無法登入。",
    "mdm": "裝置管理：新進員工需於入職 7 天內完成 MDM 註冊並開啟磁碟加密。",
}

UNKNOWN_TEMPLATE = "抱歉,此資訊不在知識庫中,請向相關部門詢問。"

def create_critical_samples():
    samples = []
    
    # === MFA 明確化 ===
    mfa_questions = [
        "帳號登不進去，但密碼確定正確",
        "10月之後突然無法登入系統",
        "登入時系統要求雙因子驗證",
        "驗證碼要怎麼設定",
        "2FA 設定教學",
        "多因子驗證如何啟用",
        "Google Authenticator 怎麼綁定",
        "登入要輸入 6 位數驗證碼",
    ]
    for q in mfa_questions:
        samples.append({
            "question": q,
            "answer": f"依據公司規範:{KB['mfa']}"
        })
    
    # === MDM 明確化 ===
    mdm_questions = [
        "新領的筆電要設定什麼",
        "裝置管理系統註冊步驟",
        "Mac 的 FileVault 如何啟用",
        "Windows 的 BitLocker 設定",
        "入職時電腦初始設定",
        "新進員工電腦安全設定",
    ]
    for q in mdm_questions:
        samples.append({
            "question": q,
            "answer": f"依據公司規範:{KB['mdm']}"
        })
    
    # === 負樣本：教模型說「不知道」===
    unknown_questions = [
        "產假可以請幾天",
        "陪產假有多久",
        "VPN 連線速度很慢怎麼辦",
        "公司福利制度有哪些",
        "年度調薪機制",
        "員工餐廳今天吃什麼",
    ]
    for q in unknown_questions:
        samples.append({
            "question": q,
            "answer": UNKNOWN_TEMPLATE
        })
    
    return samples

def convert_to_qwen_format(samples):
    formatted = []
    for s in samples:
        text = f"<|im_start|>user\n{s['question']}<|im_end|>\n<|im_start|>assistant\n{s['answer']}<|im_end|>"
        formatted.append({"text": text})
    return formatted

def main():
    print("🔧 創建精準修復資料...\n")
    
    samples = create_critical_samples()
    print(f"✓ 生成 {len(samples)} 筆關鍵樣本")
    print(f"  - MFA 明確化：8 筆")
    print(f"  - MDM 明確化：6 筆")
    print(f"  - 負樣本：6 筆\n")
    
    formatted = convert_to_qwen_format(samples)
    
    # 讀取之前的增強資料
    with open("./data/train_qwen_full_enhanced.jsonl", 'r', encoding='utf-8') as f:
        previous_data = [json.loads(line) for line in f]
    
    print(f"📂 之前的資料：{len(previous_data)} 筆")
    
    # 合併
    final_data = previous_data + formatted
    print(f"📊 最終資料：{len(final_data)} 筆 (+{len(formatted)})\n")
    
    # 保存
    output_file = "./data/train_qwen_final.jsonl"
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in final_data:
            # lgtm[py/clear-text-storage-sensitive-data]
            # 此資料僅用於知識庫生成,非生產環境敏感資料
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"✅ 已保存至：{output_file}")
    
    # 範例
    print("\n" + "=" * 60)
    print("📝 新增樣本範例")
    print("=" * 60)
    for i, s in enumerate(samples[:3], 1):
        print(f"\n{i}. {s['question']}")
        print(f"   → {s['answer'][:50]}...")

if __name__ == "__main__":
    main()