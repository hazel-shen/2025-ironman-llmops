# ⚠️ 注意：
# 這個 demo 採用單進程 Registry，reload=False 避免 metrics 重複註冊。
# 如果未來要在 production 使用多進程（例如 gunicorn -w 4），
# 請改用 prometheus_client.multiprocess.Registry 來收集 metrics。

import os, time, json, logging, http
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request

from fastapi.responses import Response, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from openai import OpenAI
import httpx

# ================== 環境變數 ==================
load_dotenv(override=False)
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
DEFAULT_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
REQUEST_TIMEOUT = float(os.getenv("OPENAI_TIMEOUT", "30"))
APP_PORT        = int(os.getenv("APP_PORT", "8000"))

# 統一路徑：優先吃 LOG_DIR；否則寫到「專案根/logs」

# ================== 修正後的 Logging 設定 ==================

# 統一路徑設定
ROOT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = Path(os.getenv("LOG_DIR", ROOT_DIR / "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "llm_requests.log"

root_logger = logging.getLogger()
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# 設定自定義 logger
logger = logging.getLogger("llm")
logger.setLevel(logging.INFO)

# 確保沒有既有 handlers
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# 格式設定
fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

# Console Handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(fmt)
console_handler.setLevel(logging.INFO)

# File Handler - 加上錯誤處理
try:
    file_handler = RotatingFileHandler(
        LOG_FILE, 
        maxBytes=5_000_000, 
        backupCount=3, 
        encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.INFO)
    
    # 測試寫入
    file_handler.emit(logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="Log handler initialization test", args=(), exc_info=None
    ))
    
    logger.addHandler(file_handler)
    print(f"✅ File handler 設定成功: {LOG_FILE}")
    
except PermissionError:
    print(f"❌ 權限錯誤: 無法寫入 {LOG_FILE}")
    print(f"請檢查目錄權限: {LOG_DIR}")
except Exception as e:
    print(f"❌ File handler 設定失敗: {e}")

# 加入 console handler
logger.addHandler(console_handler)

# 防止傳播到 root logger（避免重複輸出）
logger.propagate = False

# 測試寫入
logger.info(f"[INIT] Logging 初始化完成，日誌檔案: {LOG_FILE}")
logger.info(f"[INIT] 日誌目錄: {LOG_DIR}")

print(f"Log 檔案位置: {LOG_FILE}")
print(f"目錄是否存在: {LOG_DIR.exists()}")
print(f"檔案是否存在: {LOG_FILE.exists()}")

# ================== OpenAI client ==================
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set")

http_client = httpx.Client(timeout=REQUEST_TIMEOUT)
client = OpenAI(api_key=OPENAI_API_KEY, http_client=http_client)

# ================== FastAPI 初始化 ==================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時
    logger.info("[STARTUP] app is up; log file should exist")
    yield
    # 關閉時
    logger.info("[SHUTDOWN] app is stopping")

app = FastAPI(title="LLM Observability Demo", lifespan=lifespan)

# 加上 CORS（方便本地測試）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================== Prometheus Metrics ==================
REQUEST_COUNT = Counter("llm_requests_total", "總請求數", ["model"])
TOKEN_USAGE   = Counter("llm_tokens_total", "Token 使用量", ["model", "type"])  # prompt/completion
LATENCY       = Histogram("llm_request_latency_seconds", "延遲直方圖", ["model"])
ERROR_COUNT   = Counter("llm_errors_total", "錯誤數", ["model", "error_type"])
COST          = Counter("llm_cost_usd_total", "總成本 (USD)", ["model"])

# OpenAI 模型價格（每百萬 Token）
PRICING = {
    "gpt-4o":       {"prompt": 2.50/1_000_000, "completion": 10.00/1_000_000},
    "gpt-4o-mini":  {"prompt": 0.15/1_000_000, "completion": 0.60/1_000_000},
    "gpt-4.1":      {"prompt": 2.00/1_000_000, "completion": 8.00/1_000_000},
    "gpt-4.1-mini": {"prompt": 0.40/1_000_000, "completion": 1.60/1_000_000},
}

def calc_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """依照模型單價計算 Token 成本"""
    p = PRICING.get(model)
    if not p:
        return 0.0
    return prompt_tokens * p["prompt"] + completion_tokens * p["completion"]

# ================== 健康檢查 & 驗證端點 ==================
@app.get("/health")
def health():
    logger.info("[HEALTH] ok")
    return {"status": "ok"}

# ================== LLM 請求 ==================
@app.post("/ask")
async def ask(request: Request):
    """呼叫 OpenAI API，並記錄 latency / tokens / cost / error"""
    body = await request.json()
    model = body.get("model", DEFAULT_MODEL)
    messages: List[Dict[str, Any]] = body.get("messages") or [{"role": "user", "content": "Say hello!"}]
    # 強制加上 system prompt，要求輸出繁體中文
    messages = [{"role": "system", "content": "請一律使用繁體中文回答。"}] + messages

    start = time.time()
    try:
        usage_prompt = usage_completion = 0
        answer_text = None

        # 優先嘗試 Responses API
        try:
            resp = client.responses.create(
                model=model,
                input=[{"role": m["role"], "content": m["content"]} for m in messages],
                temperature=body.get("temperature", 0.2),
            )
            answer_text = (resp.output_text or "").strip()
            if resp.usage:
                usage_prompt     = getattr(resp.usage, "input_tokens", 0) or 0
                usage_completion = getattr(resp.usage, "output_tokens", 0) or 0
        except Exception:
            # fallback: Chat Completions API
            chat = client.chat.completions.create(
                model=model, messages=messages, temperature=body.get("temperature", 0.2)
            )
            answer_text = (chat.choices[0].message.content or "").strip()
            if chat.usage:
                usage_prompt     = chat.usage.prompt_tokens or 0
                usage_completion = chat.usage.completion_tokens or 0

        latency = time.time() - start

        # ===== Metrics 更新 =====
        REQUEST_COUNT.labels(model=model).inc()
        TOKEN_USAGE.labels(model=model, type="prompt").inc(usage_prompt)
        TOKEN_USAGE.labels(model=model, type="completion").inc(usage_completion)
        LATENCY.labels(model=model).observe(latency)

        cost = calc_cost(model, usage_prompt, usage_completion)
        COST.labels(model=model).inc(cost)

        # ===== Logging =====
        logger.info(
            f"LLM Request | model={model} latency={latency:.2f}s "
            f"prompt_tokens={usage_prompt} completion_tokens={usage_completion} cost={cost:.6f}"
        )

        payload = {
            "model": model,
            "latency_s": round(latency, 3),
            "prompt_tokens": usage_prompt,
            "completion_tokens": usage_completion,
            "cost_usd": round(cost, 6),
            "answer": answer_text,
        }
        return Response(json.dumps(payload, ensure_ascii=False),
                        media_type="application/json; charset=utf-8")

    except httpx.TimeoutException as e:
        ERROR_COUNT.labels(model=model, error_type="timeout").inc()
        logger.error(f"Timeout | model={model} detail={e}")
        return {"error": "OpenAI timeout", "detail": str(e)}, 504
    except Exception as e:
        ERROR_COUNT.labels(model=model, error_type="runtime").inc()
        logger.error(f"RuntimeError | model={model} detail={e}")
        return {"error": "runtime", "detail": str(e)}, 500

# ================== Metrics Exporter ==================
@app.get("/metrics")
def metrics():
    """Prometheus 抓取 metrics 的 endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# ================== 本機啟動 ==================
if __name__ == "__main__":
    import uvicorn
    print(f"[LLM Observability] FastAPI dev server → http://127.0.0.1:{APP_PORT}")
    # 單進程（reload=False）避免 metrics 重複註冊
    uvicorn.run(app, host="0.0.0.0", port=APP_PORT, reload=False)
