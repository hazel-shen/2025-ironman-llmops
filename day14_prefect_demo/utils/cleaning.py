import re
from bs4 import BeautifulSoup

def clean_text(raw: str) -> str:
    """
    基礎清洗：
    1) 嘗試移除 HTML 標籤（若非 HTML，不影響）
    2) 壓縮空白
    """
    try:
        soup = BeautifulSoup(raw, "html.parser")
        text = soup.get_text() or raw
    except Exception:
        text = raw
    text = re.sub(r"\s+", " ", text).strip()
    return text
