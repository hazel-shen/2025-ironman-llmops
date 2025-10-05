# api/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager

from api.routers import ask, health
from core.config import settings
from services.redis_client import get_redis

# 用 lifespan 取代 on_event
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- startup ----
    # 這裡做你原本 startup 要做的事：確認 Redis、預熱等
    try:
        r = get_redis()
        await r.ping()
    except Exception as e:
        # 依需要改成 logger.error(...)
        print(f"[startup] Redis ping failed: {e}")
        # 視情況要不要 raise；如果要服務必須有 Redis 再啟，就 raise
        # raise

    # 也可以在這裡讀設定、建 metrics 等
    print(f"[startup] METRICS_NAMESPACE = {settings.METRICS_NAMESPACE}")

    yield

    # ---- shutdown ----
    try:
        # 如果你的 redis_client 有單例，通常不強制關閉也可
        # 若一定要關閉，請確保 get_redis() 回傳的是同一個 async 連線物件
        r = get_redis()
        await r.aclose()
    except Exception as e:
        print(f"[shutdown] Redis close ignored: {e}")


app = FastAPI(title="LLM Cache Demo", lifespan=lifespan)

# 路由
app.include_router(ask.router)
app.include_router(health.router)
