from typing import List, Tuple, Dict
import re

# 假檢索資料庫（以關鍵字匹配模擬），實務可替換為向量檢索
DOCS: Dict[str, str] = {
    "doc_handbook": "本文件說明一般入職規範與遠端工作政策。",
    "doc_finance": "本文件屬機敏，包含報銷與財務審批細節。"
}

KEYWORDS = {
    "handbook": "doc_handbook",
    "入職": "doc_handbook",
    "finance": "doc_finance",
    "報銷": "doc_finance",
}

def retrieve(query: str) -> Tuple[List[str], str]:
    '''回傳(doc_ids, 拼接的 context)'''
    hits = []
    for kw, doc_id in KEYWORDS.items():
        if re.search(kw, query, re.IGNORECASE):
            if doc_id not in hits:
                hits.append(doc_id)
    # 沒命中就給預設文件
    if not hits:
        hits = ["doc_handbook"]
    context = "\n\n".join([f"[{doc_id}] {DOCS[doc_id]}" for doc_id in hits])
    return hits, context
