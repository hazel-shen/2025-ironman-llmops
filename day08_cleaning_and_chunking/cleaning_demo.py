# cleaning_demo.py
# -*- coding: utf-8 -*-
"""
極簡文件清洗流程：
1) 去雜訊（HTML → 主體文字；刪除 nav/aside/script/style/footer/目錄/廣告…）
2) 正規化（Unicode NFKC、空白、標點、數字/單位、貨幣）
3) 結構保留換行（保留標題/清單/程式碼區塊；避免硬斷行）
4) 可選：語言過濾（段落級別；支援 zh-* / en-* 正規化）
5) 去重與刪除過短片段
"""
from __future__ import annotations
import re
import unicodedata
import hashlib
from typing import List, Iterable, Tuple, Optional

# -------------------------
# 可選套件
# -------------------------
try:
    from bs4 import BeautifulSoup  # HTML 解析
except Exception:
    BeautifulSoup = None

try:
    from langdetect import detect   # 語言偵測
except Exception:
    detect = None


# -------------------------
# 1) 去雜訊（Noise Removal）
# -------------------------
NOISE_KEYWORDS = [
    # 中文
    "目錄", "返回首頁", "上一頁", "下一頁", "版權", "廣告",
    # 英文
    "Table of Contents", "TOC", "Copyright",
    "Advertisement", "Ads", "Back to home", "Next page", "Previous page",
]

def _nondestructive_keyword_cleanup(soup: "BeautifulSoup") -> None:
    """
    對含有雜訊關鍵字的節點，盡量只移除雜訊文字；
    如果整個容器都是雜訊，才整段刪除。
    """
    for kw in NOISE_KEYWORDS:
        for node in soup.find_all(string=lambda s: isinstance(s, str) and kw in s):
            parent = node.parent
            if parent and parent.name in {"p", "li", "div"}:
                # 若容器有其他內容，就只刪掉關鍵字
                full = parent.get_text(strip=True)
                if full and full != kw:
                    node.replace_with(node.replace(kw, ""))
                else:
                    parent.decompose()
            else:
                node.extract()

def strip_html_noise(html: str) -> str:
    """從 HTML 擷取正文，並刪掉常見雜訊區塊"""
    if not BeautifulSoup:
        # 沒有 bs4 → 簡單正則剝殼
        text = re.sub(r"(?is)<(script|style|nav|aside|footer|header).*?</\1>", " ", html)
        text = re.sub(r"(?is)<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    soup = BeautifulSoup(html, "html.parser")

    # 移除低價值標籤
    for tag in soup(["script", "style", "noscript", "template", "iframe"]):
        tag.decompose()
    for tag in soup.find_all(["nav", "aside", "footer", "header"]):
        tag.decompose()

    # 關鍵字清理（非破壞式）
    _nondestructive_keyword_cleanup(soup)

    # 用雙換行分隔，方便後續做段落切分
    text = soup.get_text(separator="\n\n")
    return text


# -------------------------
# 2) 正規化（Normalization）
# -------------------------
RE_REPEAT_PUNCTS = re.compile(r"([。？！；.!?;,，])\1+")
RE_SPACES = re.compile(r"[ \t\r\u00A0\u3000]+")
RE_MULTIBLANKLINES = re.compile(r"\n{3,}")

def normalize_numbers_units(s: str) -> str:
    """數字/單位正規化：10K→10,000，NT$→NTD"""
    def _expand(match: re.Match) -> str:
        num = match.group(1)
        unit = match.group(2).lower()
        try:
            val = float(num)
        except ValueError:
            return match.group(0)
        if unit == "k":
            val *= 1_000
        elif unit == "m":
            val *= 1_000_000
        # 格式化：整數加千分位，小數去尾零
        if abs(val - int(val)) < 1e-9:
            return f"{int(val):,}"
        return f"{val:,.3f}".rstrip("0").rstrip(".")
    s = re.sub(r"\b(\d+(?:\.\d+)?)([kKmM])\b", _expand, s)

    s = s.replace("NT$", "NTD ")
    s = re.sub(r"\bNTD\s*(\d)", r"NTD \1", s)
    return s

def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)       # Unicode 正規化
    text = RE_REPEAT_PUNCTS.sub(r"\1", text)         # 重複標點壓縮
    text = text.replace("\r", "\n")                  # \r → \n
    text = RE_SPACES.sub(" ", text)                  # 空白正規化
    text = normalize_numbers_units(text)             # 數字與貨幣正規化
    text = RE_MULTIBLANKLINES.sub("\n\n", text)      # 多餘空白行壓縮
    return text.strip()


# --------------------------------
# 3) 結構保留（Structure-Preserving）
# --------------------------------
FENCE = "```"

def structure_preserving_reflow(text: str) -> str:
    """
    合併一般行為段落，但保留：
    - Markdown 標題 (#)
    - 清單 (-, *, +, 1.)
    - 程式碼區塊 (``` … ```)
    - 空白行區隔
    """
    lines = text.split("\n")

    out: List[str] = []
    in_code = False
    buffer: List[str] = []

    def flush_para():
        nonlocal buffer, out
        if not buffer:
            return
        merged = " ".join([ln.strip() for ln in buffer if ln.strip() != ""])
        merged = RE_SPACES.sub(" ", merged).strip()
        if merged:
            out.append(merged)
        buffer = []

    def is_block_boundary(ln: str) -> bool:
        if not ln.strip():
            return True
        if re.match(r"^#{1,6}\s", ln):            # 標題
            return True
        if re.match(r"^(\-|\*|\+)\s+", ln):       # 無序清單
            return True
        if re.match(r"^\d+\.\s+", ln):            # 有序清單
            return True
        return False

    for ln in lines:
        if ln.strip().startswith(FENCE):
            if in_code:
                out.append(ln.rstrip())
                in_code = False
            else:
                flush_para()
                in_code = True
                out.append(ln.rstrip())
            continue

        if in_code:
            out.append(ln.rstrip())
            continue

        if is_block_boundary(ln):
            flush_para()
            out.append(ln.rstrip())
        else:
            buffer.append(ln)

    flush_para()

    # 確保區塊之間最多一行空白
    final: List[str] = []
    for i, ln in enumerate(out):
        final.append(ln)
        if i < len(out) - 1:
            curr_blank = (ln.strip() == "")
            next_blank = (out[i+1].strip() == "")
            if not curr_blank and not next_blank:
                final.append("")

    return "\n".join(final).strip()


# -----------------------------
# 4) 語言過濾（Optional）
# -----------------------------
def _norm_lang(code: str) -> str:
    """把 zh-cn/zh-tw → zh；en-us/en-gb → en"""
    if not code:
        return "unknown"
    code = code.lower()
    if code.startswith("zh"):
        return "zh"
    if code.startswith("en"):
        return "en"
    return code

def filter_language(paragraphs: Iterable[str], keep_langs: Tuple[str, ...] = ("zh", "en")) -> List[str]:
    if detect is None:
        return list(paragraphs)
    kept = []
    for p in paragraphs:
        txt = p.strip()
        if not txt:
            continue
        probe = txt if len(txt) > 40 else (txt + "。" * (40 - len(txt)))
        try:
            lang_raw = detect(probe)
        except Exception:
            lang_raw = "unknown"
        lang = _norm_lang(lang_raw)
        if lang in keep_langs or lang == "unknown":
            kept.append(p)
    return kept


# ----------------------------------------
# 5) 去重與短片段過濾
# ----------------------------------------
def dedupe_and_drop_short(paragraphs: Iterable[str], min_chars: int = 10) -> List[str]:
    seen = set()
    out = []
    for p in paragraphs:
        t = p.strip()
        if len(t) < min_chars:
            continue
        h = hashlib.sha1(t.encode("utf-8")).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        out.append(t)
    return out


# -------------------------
# Pipeline 入口
# -------------------------
def clean_document(raw: str, is_html: bool = True, lang_keep: Optional[Tuple[str, ...]] = None) -> List[str]:
    """清洗文件並回傳段落清單"""
    text = strip_html_noise(raw) if is_html else raw
    text = normalize_text(text)
    text = structure_preserving_reflow(text)
    paragraphs = [p for p in text.split("\n") if p.strip() != ""]
    if lang_keep:
        paragraphs = filter_language(paragraphs, keep_langs=lang_keep)
    paragraphs = dedupe_and_drop_short(paragraphs, min_chars=10)
    return paragraphs


# -------------------------
# 範例執行
# -------------------------
if __name__ == "__main__":
    raw_html = """
    <html>
      <head><title>公司規章</title></head>
      <body>
        <nav>返回首頁｜目錄｜下一頁</nav>
        <aside>廣告：買一送一！</aside>
        <h1>公司制度</h1>
        <p>加班申請：需事先提出，加班工時可折換補休！！！</p>
        <p>出差申請：需填寫出差單，並附上行程與預算。  請參考「Table of Contents」。</p>
        <p>獎金上限為 10K 或 NT$5000，以較低者為準。</p>
        <script>alert('ads')</script>
        <footer>Copyright 2025</footer>

        <h2>清單範例</h2>
        <ul>
          <li> A 條款</li>
          <li> B 條款</li>
        </ul>

        <pre>
        Some      code block
        should   keep      spaces
        </pre>

        <p>English note: Budget cap is 5k only?!</p>

        <p>重複段落示例。</p>
        <p>重複段落示例。</p>

        <p>短</p>

        <p>
        {code}
        </p>
        <p>結束</p>
      </body>
    </html>
    """.replace("{code}", "```\\nprint('hi')\\n```")

    cleaned = clean_document(raw_html, is_html=True, lang_keep=("zh", "en"))
    print("=== 清洗後段落 ===")
    for i, p in enumerate(cleaned, 1):
        print(f"[{i}] {p}")
