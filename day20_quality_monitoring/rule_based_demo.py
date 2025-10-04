# -*- coding: utf-8 -*-
# rule_based_demo.py
"""
Rule-based Check Demo
以簡單規則快速攔截明顯錯誤：敏感路徑、URL、（可選）白名單、JSON 粗檢
"""

import re
from typing import List


def rule_based_check(answer: str) -> List[str]:
    """
    回傳命中的告警訊息列表；可擴充黑/白名單、JSON schema、單位/數值範圍檢查等。
    """
    issues: List[str] = []

    # 1) 敏感系統路徑（示意）
    if "/etc/" in answer:
        issues.append("⚠️ 回答可能包含不該暴露的伺服器路徑")

    # 2) 若聲稱有連結，卻沒有有效 URL
    if "http" in answer and not re.search(r"http[s]?://", answer):
        issues.append("⚠️ 回答提到連結但缺少有效的 URL")

    # 3) （可選）白名單關鍵詞（確保回答引用文件常見詞彙）
    # whitelist = {"VPN", "連線", "帳號", "安裝軟體"}
    # if not any(w in answer for w in whitelist):
    #     issues.append("⚠️ 回答未引用文件中的關鍵詞（白名單檢查）")

    # 4) （可選）JSON 結構粗檢（極簡示意）
    if "{" in answer and "}" not in answer:
        issues.append("⚠️ JSON 結構疑似不完整")

    return issues


if __name__ == "__main__":
    # ✅/❌ 正反例子
    examples = [
        ("範例 A（❌ 敏感路徑）", "你可以在 /etc/vpn/config 找到設定檔。"),
        ("範例 B（❌ 提到連結但無有效 URL）", "詳細說明請見公司內網，連結在 http 部分。"),
        ("範例 C（❌ JSON 結構不完整）", "請回傳如下設定：{ \"enable\": true, "),
        ("範例 D（✅ 合理回答）", "依文件步驟：先安裝 VPN 軟體，以公司帳號登入後再嘗試連線。"),
        ("範例 E（✅ 合理且含有效 URL）", "步驟與注意事項請見 https://intranet.example.com/vpn-guide 。"),
    ]

    for label, answer in examples:
        issues = rule_based_check(answer)
        if issues:
            print(f"{label}\n回答：{answer}\nRule-based 攔截: {issues}\n")
        else:
            print(f"{label}\n回答：{answer}\nRule-based 通過 ✅\n")
