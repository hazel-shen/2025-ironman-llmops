# tests/conftest.py
"""
Pytest shared configuration & fixtures.

功能：
1) 修正 sys.path，避免 `ModuleNotFoundError: No module named 'registry'`
2) 提供共用 fixtures：prompts_dir、reg (PromptRegistry 實例)
"""

import sys
from pathlib import Path
import pytest

# --- 1) 修正 sys.path：把專案根目錄加入匯入路徑 -------------------------------
# tests/ 目錄的上層即專案根目錄
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# --- 2) 共用 fixtures -------------------------------------------------------

@pytest.fixture(scope="session")
def prompts_dir() -> str:
    """
    回傳 prompts 目錄的字串路徑，例如：<project_root>/prompts
    """
    p = PROJECT_ROOT / "prompts"
    assert p.exists(), f"[conftest] Prompts folder not found: {p}"
    return str(p)

@pytest.fixture(scope="session")
def reg(prompts_dir):
    """
    建立一次性的 PromptRegistry 實例，供所有測試共用。
    """
    from registry.registry import PromptRegistry  # 匯入放這裡，確保 sys.path 已修正
    return PromptRegistry(prompts_dir)

# ▼ 如果你想在變數缺漏時讓渲染直接報錯，可改用 StrictUndefined。
#    這需要你在 registry.PromptRegistry 中用 jinja2.Environment 建立 Template。
# from jinja2 import Environment, StrictUndefined
# env = Environment(un
