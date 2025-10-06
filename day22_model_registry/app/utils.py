from typing import Union
from .models import Stage

# 定義允許的狀態轉換
_ALLOWED = {
    Stage.none:       {Stage.staging},
    Stage.staging: {Stage.production, Stage.archived},
    Stage.production: {Stage.staging, Stage.archived},
    Stage.archived: set(),  # Archived 無法再轉出
}

def to_enum(x) -> Stage:
    """將輸入統一轉成 Stage Enum；接受 'None'/'none' 等大小寫變體。"""
    if isinstance(x, Stage):
        return x
    if x is None:
        return Stage.none
    s = str(x).strip().lower()
    if s == "none":
        return Stage.none
    if s == "staging":
        return Stage.staging
    if s == "production":
        return Stage.production
    if s == "archived":
        return Stage.archived
    # 明確拋錯，讓上層回傳 400
    raise ValueError(f"Invalid stage '{x}'. Allowed: None, Staging, Production, Archived.")


def can_transition(from_stage: Union[str, Stage], to_stage: Union[str, Stage]) -> bool:
    fr, to = to_enum(from_stage), to_enum(to_stage)
    # 用 get 防衛以免 KeyError（理論上不會發生）
    return to in _ALLOWED.get(fr, set())
