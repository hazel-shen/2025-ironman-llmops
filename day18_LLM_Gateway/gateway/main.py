# gateway/main.py
import os
import time
import logging
from collections import defaultdict, deque
from typing import Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from openai import OpenAI
# === Prometheus Metrics（minimal set） ===
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from services.retrieval_service import retrieve_best

REQS = Counter(
    "gateway_requests_total", "Total HTTP requests",
    labelnames=["route", "method", "status"]
)
LAT = Histogram(
    "gateway_request_duration_seconds", "Request latency (seconds)",
    labelnames=["route", "method"]
)
ERRS = Counter(
    "gateway_errors_total", "Errors by type",
    labelnames=["route", "type"]
)

# ============================================================
# 🟠 Logging：同時輸出 console + 檔案 gateway.log
# ============================================================
root_logger = logging.getLogger()
if not root_logger.handlers:
    root_logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    # Console Handler
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    root_logger.addHandler(ch)

    # File Handler
    fh = logging.FileHandler("gateway.log", encoding="utf-8")
    fh.setFormatter(fmt)
    root_logger.addHandler(fh)

log = logging.getLogger(__name__)

# ============================================================
# 🟢 FastAPI 初始化 + CORS
# ============================================================
app = FastAPI(title="LLM Gateway (Day18)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 開發先放寬；上線請改白名單
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 🟢 讀取環境變數 / 初始化 OpenAI
# ============================================================
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("沒有找到 OPENAI_API_KEY，請在 .env 或環境變數中設定！")

OPENAI_TIMEOUT = float(os.getenv("OPENAI_TIMEOUT", "20"))
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")
client = OpenAI(timeout=OPENAI_TIMEOUT, max_retries=0)

# ============================================================
# 🟢 前端頁面（serve index.html）
# ============================================================
BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"

@app.get("/")
def root():
    idx = FRONTEND_DIR / "index.html"
    if idx.exists():
        return FileResponse(idx)
    return JSONResponse({"error": "frontend/index.html not found"}, status_code=404)

# 若有 js/css/圖檔，可放在 /_static 底下
app.mount("/_static", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

# ============================================================
# 🟢 健康檢查
# ============================================================
@app.get("/healthz")
def healthz():
    return {"ok": True}

# ============================================================
# 🟢 metrics 
# 目的：
# - 暴露 Prometheus 可抓取的指標（text exposition format）。
# - 部署時在 Prometheus 設定 scrape_configs 指向此端點即可。
# ============================================================
@app.get("/metrics")
def metrics():
    # CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# ============================================================
# 🟢 記憶體限流 (In-Memory Rate Limit)
#   - Demo 用：每 IP 每分鐘最多 10 次
#   - 程式重啟會清空；多 worker/多機不共享狀態；LB/水平擴展時無法全局生效
#   - 生產環境請換 Redis / 雲端 API Gateway
# ============================================================
_WINDOW_SEC = int(os.getenv("RATE_LIMIT_WINDOW_SEC", "60"))
_LIMIT = int(os.getenv("RATE_LIMIT_MAX_PER_IP", "10"))
_BUCKETS: dict[str, deque] = defaultdict(deque)

def in_memory_rate_limit(request: Request):
    ip = request.client.host
    now = time.time()
    dq = _BUCKETS[ip]

    # 移除視窗外的請求
    while dq and now - dq[0] > _WINDOW_SEC:
        dq.popleft()

    if len(dq) >= _LIMIT:
        raise HTTPException(status_code=429, detail="Too Many Requests (demo limiter)")
    dq.append(now)

# ============================================================
# 🟢 小工具：檢索 + LLM 回答
# ============================================================
def handle_ask(question: str, temperature: float = 0.2) -> Dict[str, Any]:
    q = (question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="question is required")

    # 1) 檢索知識庫
    context, dist = retrieve_best(q, k=3)

    # 2) 呼叫 LLM
    messages = [
        {"role": "system", "content": "你是一個企業 FAQ 助理。"},
        {"role": "user", "content": f"根據以下知識庫內容回答：\n{context}\n\n問題：{q}"},
    ]
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=temperature,
    )
    answer = resp.choices[0].message.content

    return {
        "question": q,
        "context": context,
        "answer": answer,
        "debug": {"l2": dist, "model": CHAT_MODEL}
    }

# ============================================================
# 🟠 /ask：POST 專用（含記憶體限流 + 簡單 Logging）
#   - 記錄每次請求的來源與問題
#   - 成功與失敗都會 log
# ============================================================
@app.post("/ask")
def ask(payload: Dict[str, Any], request: Request):
    # 🟢 限流檢查
    in_memory_rate_limit(request)

    q = (payload.get("question") or "").strip()
    temp = float(payload.get("temperature", 0.2))

    # 🟠 Logging：記錄來源與問題
    log.info(f"[ASK] ip={request.client.host} q={q!r} temp={temp}")

    start = time.time()
    try:
        result = handle_ask(q, temp)
        log.info(f"[ASK] success in {time.time()-start:.2f}s, answer_len={len(result['answer'])}")
        return result
    except HTTPException:
        log.exception("[ASK] http error")
        raise
    except Exception:
        log.exception("[ASK] failed")
        return JSONResponse(status_code=500, content={"error": "internal error"})

# ============================================================
# Metrics Middleware
# 目的：
# - 統一量測所有 API 的請求數、延遲（p50/p95 可由 Prometheus/Grafana 計算）、錯誤類型。
# - 不需要每個路由都手刻計數邏輯。
# ============================================================
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    route = request.url.path or "unknown"
    method = request.method

    # 不要量測 /metrics 本身，避免自我干擾
    if route == "/metrics":
        return await call_next(request)

    with LAT.labels(route, method).time():
        status = "500"
        try:
            resp = await call_next(request)
            status = str(resp.status_code)
            return resp
        except HTTPException as he:
            status = str(he.status_code)
            ERRS.labels(route, "http").inc()
            raise
        except Exception:
            ERRS.labels(route, "unhandled").inc()
            raise
        finally:
            REQS.labels(route, method, status).inc()