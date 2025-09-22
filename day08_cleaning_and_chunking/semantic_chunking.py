# semantic_chunking.py
import re

def chunk_semantic(text):
    # 先斷句（技術步驟，不特別當作一種方法）
    sentences = re.split(r"[。！？]", text)
    sentences = [s.strip()+"。" for s in sentences if s.strip()]

    chunks, cur, cur_lab = [], [], None
    for s in sentences:
        lab = "attend" if any(k in s for k in ATTEND) else "admin"
        if cur_lab is None or lab == cur_lab:
            cur.append(s); cur_lab = lab
        else:
            chunks.append("".join(cur)); cur = [s]; cur_lab = lab
    if cur:
        chunks.append("".join(cur))
    return chunks

sample = """加班申請需事先提出，加班工時可折換補休。
出差申請需填寫出差單，並附上行程與預算。
報銷規則需要提供發票，金額超過 1000 需經理簽核。
員工請假需提前一天申請，緊急情況可事後補辦。
遲到超過三次需與主管面談，嚴重者列入考核。"""

ADMIN  = {"加班","出差","報銷","發票","簽核","預算"}
ATTEND = {"請假","遲到","面談","考核","緊急"}

print(chunk_semantic(sample))
