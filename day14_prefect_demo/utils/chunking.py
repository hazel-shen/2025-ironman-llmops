from typing import List
import re

def simple_sentence_split(text: str) -> List[str]:
    """
    超簡單中文句子切分：以句號/驚嘆號/問號作為分界。
    """
    sents = re.split(r"(?<=[。！？\?])\s*", text)
    return [s.strip() for s in sents if s and s.strip()]

def chunk_text(text: str, max_chars: int = 180, overlap: int = 40) -> List[str]:
    """
    以字數近似控制 chunk 長度，並加入 overlap。
    輕量、不依賴 heavy NLP，適合教學 demo。
    """
    sents = simple_sentence_split(text)
    chunks: List[str] = []
    buf = ""

    for s in sents:
        if len(buf) + len(s) + (1 if buf else 0) <= max_chars:
            buf = (buf + " " + s).strip()
        else:
            if buf:
                chunks.append(buf)
                # 取尾端 overlap 段落 + 新句子
                tail = buf[-overlap:] if overlap > 0 else ""
                buf = (tail + " " + s).strip()
            else:
                chunks.append(s[:max_chars])
                buf = s[max_chars-overlap:] if overlap > 0 else ""

    if buf:
        chunks.append(buf)

    return chunks
