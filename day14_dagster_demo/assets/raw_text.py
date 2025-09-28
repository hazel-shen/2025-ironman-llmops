from dagster import asset
from .common import RAW_FILE

# 📄 資產：raw_text
# 功能：讀取最原始的輸入文件內容（raw.txt）
@asset(description="原始文本")
def raw_text(context) -> str:
    t = RAW_FILE.read_text(encoding="utf-8")
    context.log.info(f"讀取原始檔案 {RAW_FILE}，長度={len(t)}")
    return t
