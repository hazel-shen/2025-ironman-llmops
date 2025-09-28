from typing import List
from dagster import asset
from .cleaned_text import cleaned_text
from .common import chunk_text

# 📄 資產：chunks
# 功能：把清理後的文本切成多個小段落（chunk），利於後續向量化
@asset(description="切片結果")
def chunks(context, cleaned_text: str) -> List[str]:
    cs = chunk_text(cleaned_text)
    context.log.info(f"產生 {len(cs)} 個 chunk")
    return cs
