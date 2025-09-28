from dagster import asset
from .raw_text import raw_text
from .common import clean_text

# 📄 資產：cleaned_text
# 功能：將原始文本清理（去除雜訊、空白等），產生乾淨文本
@asset(description="清洗後文本")
def cleaned_text(context, raw_text: str) -> str:
    t = clean_text(raw_text)
    context.log.info(f"清洗後長度={len(t)}")
    return t
