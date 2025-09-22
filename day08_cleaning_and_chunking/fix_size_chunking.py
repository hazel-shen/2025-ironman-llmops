# fix_size_chunking.py
def chunk_fixed(text, size=20, overlap=5):
    words = list(text)  # 以「字元」為單位
    chunks = []
    for i in range(0, len(words), size - overlap):
        chunks.append("".join(words[i:i+size]))
    return chunks

sample = """加班申請需事先提出，加班工時可折換補休。
出差申請需填寫出差單，並附上行程與預算。
報銷規則需要提供發票，金額超過 1000 需經理簽核。
員工請假需提前一天申請，緊急情況可事後補辦。
遲到超過三次需與主管面談，嚴重者列入考核。"""

print(chunk_fixed(sample, size=20, overlap=5))
