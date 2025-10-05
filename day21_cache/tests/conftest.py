# tests/conftest.py
# --- 把專案根目錄加到匯入路徑 ---
import os
import sys
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import pytest
import httpx
import redis.asyncio as aioredis  # redis-py 5.x

# 測試時啟用語意快取
os.environ.setdefault("ENABLE_EMBED_CACHE", "true")

from api.main import app
from core.config import settings


@pytest.fixture(autouse=True)
async def _isolate_redis_per_test(monkeypatch):
    """
    每個測試建立『自己的』Redis 連線，並把應用程式取用的入口全部換成這個連線。
    - monkeypatch get_redis()
    - 也 monkeypatch 模組層單例 redis_client（若存在）
    - 測試前後 flushdb，最後 aclose()
    """
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    import services.redis_client as rc
    # 換掉 get_redis()
    monkeypatch.setattr(rc, "get_redis", lambda: r, raising=False)
    # 若模組裡有單例，直接覆蓋成這個測試的連線
    if hasattr(rc, "redis_client"):
        monkeypatch.setattr(rc, "redis_client", r, raising=False)

    # 乾淨化
    await r.flushdb()
    try:
        yield
    finally:
        try:
            await r.flushdb()
        finally:
            await r.aclose()


@pytest.fixture
def lower_threshold(monkeypatch):
    """把語意快取門檻調低，保證測試時容易命中。"""
    monkeypatch.setattr(settings, "EMBED_SIM_THRESHOLD", 0.0, raising=False)
    return settings.EMBED_SIM_THRESHOLD


@pytest.fixture
def mock_llm(monkeypatch):
    """mock 掉 LLMService.chat 與 embed，避免外部 API 與費用。"""
    import services.llm as llm_mod

    async def fake_chat(self, question: str):
        return llm_mod.LLMResult(
            answer=f"[fake answer] {question}",
            prompt_tokens=4,
            completion_tokens=8,
            cost_usd=0.0005,
        )

    # 固定向量（1536 維），確保相似度=1
    async def fake_embed(self, text: str):
        dim = 1536
        v = [0.0] * dim
        v[0] = 1.0
        return v

    monkeypatch.setattr(llm_mod.LLMService, "chat", fake_chat, raising=False)
    monkeypatch.setattr(llm_mod.LLMService, "embed", fake_embed, raising=False)
    return True


@pytest.fixture
async def client():
    """httpx 0.28+ 用 ASGITransport 呼叫 FastAPI app（in-process）"""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
