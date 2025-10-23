#!/usr/bin/env python3
"""
Qwen2.5 評估集生成器 v1.0 - 從 BLOOM v4 改寫
策略: 從訓練集的 4 種風格中，隨機抽取未用於訓練的問法
格式: Qwen2.5-Instruct 對話格式

使用方式:
    python scripts/generate_qwen_eval_set.py
"""

import json
import random
from pathlib import Path

# ============================================
# 評估集問題 - 與 BLOOM 版本相同
# ============================================
EVAL_QUESTIONS = {
    "doc_611a2e74": [  # VPN - 5個評估問題
        "vpn 連線逾時",
        "VPN 連不上怎麼辦?",
        "新人 vpn 設定",
        "無法存取公司內部網路",
        "2025 vpn 設定流程"
    ],
    
    "doc_30059bd8": [  # 遠端辦公
        "新人可以居家辦公嗎",
        "剛入職可以申請居家辦公嗎?",
        "試用期能遠端嗎",
        "轉正前能 wfh 嗎",
        "遠端辦公資格"
    ],
    
    "doc_d8148fc3": [  # MFA
        "10月後沒開 mfa 會怎樣",
        "2025年10月後沒設定雙因子驗證會發生什麼?",
        "帳號登不進去",
        "雙因子驗證設定",
        "強制啟用 MFA 的時間"
    ],
    
    "doc_2cc7937d": [  # 密碼重設
        "密碼忘了去哪重置",
        "公司帳號密碼忘了要去哪裡重置?",
        "帳號被鎖住",
        "重置密碼頁面",
        "員工編號忘了怎麼查"
    ],
    
    "doc_f7379232": [  # 郵件附件
        "50MB 簡報檔怎麼寄",
        "想寄 50MB 的簡報檔給客戶",
        "郵件附件超過上限",
        "大檔案分享",
        "雲端連結怎麼產生"
    ],
    
    "doc_838f69ae": [  # 報銷
        "發票超過一個月還能報嗎",
        "出差發票超過一個月還能報帳嗎?",
        "報帳期限",
        "發票遺失",
        "逾期報帳處理"
    ],
    
    "doc_37f6edeb": [  # 差旅等級
        "出差可以坐商務車廂嗎",
        "國內出差可以坐商務車廂嗎?",
        "高鐵商務艙",
        "升等誰批",
        "國外機票等級"
    ],
    
    "doc_c7a8eb99": [  # 資安回報
        "收到奇怪郵件要跟誰說",
        "收到奇怪的郵件要跟誰說?",
        "釣魚郵件處理",
        "疑似詐騙回報",
        "資安通報管道"
    ],
    
    "doc_4941edf7": [  # MDM
        "新人筆電設定",
        "剛到職的筆電要設定什麼?",
        "mdm 怎麼註冊",
        "磁碟加密",
        "7天內完成設定"
    ],
    
    "doc_e4d9d352": [  # 資料保留
        "客服對話保留多久",
        "客服對話會保留多久?",
        "聊天記錄會刪除嗎",
        "180天後資料",
        "審計日誌保留期限"
    ],
    
    "doc_51f8beab": [  # 請假
        "忘記請假可以補嗎",
        "昨天忘記請假今天可以補嗎?",
        "事後補登假單",
        "臨時請假",
        "請假要提前嗎"
    ],
    
    "doc_2dfaeccd": [  # 會議室
        "可以同時訂兩間會議室嗎",
        "部門會議可以同時訂兩間會議室嗎?",
        "會議室上限",
        "訂3間會議室",
        "會議室取消流程"
    ],
    
    "doc_540013cd": [  # 檔案保存
        "程式碼一定要放雲端嗎",
        "開發的程式碼一定要放雲端嗎?",
        "重要文件存放",
        "只存電腦可以嗎",
        "雲端硬碟在哪"
    ],
    
    "doc_e761823c": [  # 加班
        "週末加班要誰批",
        "六日要加班需要找誰核准?",
        "假日加班申請",
        "平日加班要申請嗎",
        "雙重核准意思"
    ],
    
    "doc_2b808180": [  # 資安培訓
        "資安測驗沒過會怎樣",
        "資安線上測驗如果沒通過會怎樣?",
        "每年要考資安嗎",
        "帳號被停用原因",
        "線上測驗在哪考"
    ]
}

# ============================================
# 無答案問題 - 10個負樣本
# ============================================
EVAL_UNANSWERABLE = [
    ("公司有員工餐廳嗎", "抱歉,知識庫中未記載此規定,建議向總務部門確認。"),
    ("可以申請育嬰假嗎", "抱歉,此資訊不在我的知識範圍內,請向人資部門詢問。"),
    ("部門聚餐費用可以報銷嗎", "抱歉,知識庫未記載此規定,請洽財務部門。"),
    ("轉調其他部門的流程", "抱歉,此資訊不在知識庫中,請向人資部門詢問。"),
    ("公司有員工宿舍嗎", "抱歉,知識庫未記載,建議向行政部門確認。"),
    ("VPN 可以在國外用嗎", "抱歉,知識庫未記載此規定,請洽 IT 部門。"),
    ("會議室可以外借嗎", "抱歉,此資訊不在知識庫中,請洽總務部門。"),
    ("公司有交通車嗎", "抱歉,知識庫未記載,建議向行政部門確認。"),
    ("特休可以賣掉嗎", "抱歉,此資訊不在知識庫中,請向人資部門詢問。"),
    ("加班可以換補休嗎", "抱歉,知識庫未記載此規定,請洽人資部門。")
]

def format_qwen_qa(question, answer):
    """
    格式化為 Qwen2.5-Instruct 對話格式
    輸入: 問題、答案
    輸出: <|im_start|>user\n問題<|im_end|>\n<|im_start|>assistant\n答案<|im_end|>
    """
    return (
        f"<|im_start|>user\n{question}<|im_end|>\n"
        f"<|im_start|>assistant\n{answer}<|im_end|>"
    )

def load_kb(filepath="data/kb.jsonl"):
    """載入知識庫"""
    kb = []
    kb_path = Path(filepath)
    
    if not kb_path.exists():
        raise FileNotFoundError(f"找不到知識庫檔案: {filepath}")
    
    with open(kb_path, 'r', encoding='utf-8') as f:
        for line in f:
            kb.append(json.loads(line))
    
    return kb

def generate_eval_data(kb):
    """生成 Qwen 格式評估資料"""
    eval_data = []
    
    # === 1. 有答案的問題 ===
    for doc in kb:
        doc_id = doc['doc_id']
        if doc_id not in EVAL_QUESTIONS:
            continue
        
        questions = EVAL_QUESTIONS[doc_id]
        answer_text = f"依據公司規範:{doc['text']}"
        
        for q in questions:
            formatted = format_qwen_qa(q, answer_text)
            eval_data.append({"text": formatted})
    
    # === 2. 無答案的問題 ===
    for q, a in EVAL_UNANSWERABLE:
        formatted = format_qwen_qa(q, a)
        eval_data.append({"text": formatted})
    
    # 不打亂順序，保持知識點分組（方便分析）
    
    return eval_data

def save_jsonl(data, filepath):
    """儲存為 JSONL 格式"""
    output_path = Path(filepath)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

def analyze_coverage(eval_data, train_file="data/train_qwen_v1.jsonl"):
    """分析評估集與訓練集的重疊度"""
    # 載入訓練集
    train_questions = set()
    try:
        with open(train_file, 'r', encoding='utf-8') as f:
            for line in f:
                item = json.loads(line)
                # 提取問題部分 (在 <|im_start|>user 和 <|im_end|> 之間)
                text = item['text']
                if '<|im_start|>user\n' in text and '<|im_end|>' in text:
                    start = text.index('<|im_start|>user\n') + len('<|im_start|>user\n')
                    end = text.index('<|im_end|>', start)
                    question = text[start:end].strip()
                    train_questions.add(question)
    except FileNotFoundError:
        print(f"⚠️  找不到訓練集檔案: {train_file}")
        return
    
    # 分析評估集
    eval_questions = []
    for item in eval_data:
        text = item['text']
        if '<|im_start|>user\n' in text and '<|im_end|>' in text:
            start = text.index('<|im_start|>user\n') + len('<|im_start|>user\n')
            end = text.index('<|im_end|>', start)
            question = text[start:end].strip()
            eval_questions.append(question)
    
    # 計算重疊
    overlap = sum(1 for q in eval_questions if q in train_questions)
    
    print(f"\n🔍 重疊度分析:")
    print(f"   訓練集問題數: {len(train_questions)}")
    print(f"   評估集問題數: {len(eval_questions)}")
    print(f"   完全重疊: {overlap} 個 ({overlap/len(eval_questions)*100:.1f}%)")
    print(f"   風格相似: ~{len(eval_questions)-overlap} 個")
    
    if overlap > len(eval_questions) * 0.3:
        print(f"   ⚠️  重疊度較高，可能導致過擬合")
    else:
        print(f"   ✅ 重疊度適中，能測試泛化能力")

def main():
    print("=" * 60)
    print("🎯 Qwen2.5 評估集生成器 v1.0")
    print("=" * 60)
    
    # 載入知識庫
    print("\n📚 載入知識庫...")
    kb = load_kb("data/kb.jsonl")
    print(f"✅ 載入 {len(kb)} 條規範")
    
    # 生成評估資料
    print("\n🔨 生成評估資料...")
    eval_data = generate_eval_data(kb)
    
    # 儲存
    output_file = "data/eval_qwen_v1.jsonl"
    save_jsonl(eval_data, output_file)
    
    print(f"\n✅ 評估集已儲存: {output_file}")
    print(f"   總筆數: {len(eval_data)}")
    
    # 統計資訊
    has_answer = sum(1 for item in eval_data if "依據公司規範" in item['text'])
    no_answer = len(eval_data) - has_answer
    
    print(f"\n📈 實際分布:")
    print(f"   有答案: {has_answer} 筆 ({has_answer/len(eval_data)*100:.1f}%)")
    print(f"   無答案: {no_answer} 筆 ({no_answer/len(eval_data)*100:.1f}%)")
    
    print(f"\n🎨 格式特點:")
    print(f"   ✅ Qwen2.5-Instruct 對話格式")
    print(f"   ✅ 使用 <|im_start|> / <|im_end|> 標記")
    print(f"   ✅ 移除 BLOOM 的 <|endoftext|> 標記")
    print(f"   ✅ 每個知識點 5 個變體")
    print(f"   ✅ 總共 {has_answer//5} 個知識點")
    
    # 顯示範例
    print(f"\n📝 格式範例:")
    sample = eval_data[0]['text']
    print(sample[:200] + "...")
    
    # 分析重疊度
    analyze_coverage(eval_data)
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()