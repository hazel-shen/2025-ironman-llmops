# sentence_base_chunking.py
import re

def chunk_sentence(text):
    sentences = re.split(r"。|！|？|\n", text)
    return [s.strip() for s in sentences if s.strip()]


sample = """加班申請需事先提出，加班工時可折換補休。
出差申請需填寫出差單，並附上行程與預算。
報銷規則需要提供發票，金額超過 1000 需經理簽核。
員工請假需提前一天申請，緊急情況可事後補辦。
遲到超過三次需與主管面談，嚴重者列入考核。
"""

print(chunk_sentence(sample))