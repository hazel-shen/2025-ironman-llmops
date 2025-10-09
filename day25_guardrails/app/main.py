from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from app.guardrails import Guardrails, sanitize_input
import os
import time
import yaml

app = FastAPI()

# === Prometheus 指標 ===
REQUEST_COUNT = Counter(
    "gateway_requests_total",
    "總請求數",
    ["route", "method"]
)

REQUEST_BLOCKED = Counter(
    "gateway_requests_blocked_total",
    "被擋下的請求數",
    ["route", "method", "reason"]  # reason = input / output / acl
)

REDACTIONS_TOTAL = Counter(
    "gateway_redactions_total",
    "去識別化次數",
    ["type"]  # type = email / phone
)

ACL_DENIED = Counter(
    "gateway_acl_denied_total",
    "因 ACL 被拒次數",
    ["doc_id", "role"]
)

REQUEST_LATENCY = Histogram(
    "gateway_request_latency_seconds",
    "請求延遲（秒）",
    ["route", "method"]
)

# === Policy 載入 + 熱更新 ===
policy_path = os.path.join(os.path.dirname(__file__), "..", "policy.yaml")
policy_mtime = None
policy = {}
guardrails = None

def load_policy(force: bool = False):
    """讀取 policy.yaml，若檔案更新則重載。"""
    global policy, guardrails, policy_mtime
    mtime = os.path.getmtime(policy_path)
    if force or policy_mtime is None or mtime > policy_mtime:
        with open(policy_path, "r", encoding="utf-8") as f:
            policy = yaml.safe_load(f)
        guardrails = Guardrails(policy)
        policy_mtime = mtime
        print(f"[INFO] policy.yaml reloaded (mtime={policy_mtime})")

# 服務啟動先載入一次
load_policy(force=True)

# === 文件路由規則（簡單關鍵字 → doc_id）===
def route_docs(query: str) -> str:
    q = (query or "").lower()
    finance_keywords = ["finance", "財務", "報銷", "預算", "會計"]
    if any(kw in q for kw in finance_keywords):
        return "doc_finance"
    return "doc_handbook"


@app.get("/health")
async def health():
    # health 也順便確保 policy 最新
    load_policy()
    return {
        "status": "ok",
        "mode": policy.get("runtime", {}).get("mode", "enforce")
    }


@app.get("/metrics")
async def metrics():
    # 回傳 Prometheus exposition format（純文字）
    return Response(generate_latest(), media_type="text/plain")


@app.post("/ask")
async def ask(request: Request):
    start_time = time.time()

    # 每次請求前檢查 policy 是否更新
    load_policy()

    data = await request.json()
    query = sanitize_input(data.get("query", ""))
    user = data.get("user", {}) or {}
    user_role = user.get("role", "guest")

    # 1) 讀取模式：Header > policy.yaml
    mode = request.headers.get("X-Guardrails-Mode") \
        or policy.get("runtime", {}).get("mode", "enforce")

    meta = {
        "violations": [],
        "redactions": 0,
        "blocked": False,
        "retrieved_docs": [],
        "mode": mode,
    }

    # === Input Guardrails（依 mode）===
    blocked, violations = guardrails.check_input(query, mode)
    meta["violations"].extend(violations)
    if blocked:  # enforce 模式才會回 400
        meta["blocked"] = True
        REQUEST_COUNT.labels(route="/ask", method="POST").inc()
        REQUEST_BLOCKED.labels(route="/ask", method="POST", reason="input").inc()
        REQUEST_LATENCY.labels(route="/ask", method="POST").observe(time.time() - start_time)
        return JSONResponse(status_code=400, content={"answer": None, "meta": meta})

    # === 檢索：以簡單關鍵字決定 doc ===
    doc_id = route_docs(query)

    # === ACL（依 mode）===
    allowed, violations = guardrails.enforce_acl(user_role, [doc_id], mode)
    meta["violations"].extend(violations)
    if not allowed:  # enforce 模式才會回 403
        meta["blocked"] = True
        REQUEST_COUNT.labels(route="/ask", method="POST").inc()
        REQUEST_BLOCKED.labels(route="/ask", method="POST", reason="acl").inc()
        # 計入第一個拒絕文件與角色
        if violations:
            # violations 內容如 "acl_denied:doc_finance"
            denied = violations[0].split(":", 1)[-1]
            ACL_DENIED.labels(doc_id=denied, role=user_role).inc()
        REQUEST_LATENCY.labels(route="/ask", method="POST").observe(time.time() - start_time)
        return JSONResponse(status_code=403, content={"answer": None, "meta": meta})

    meta["retrieved_docs"].append(doc_id)

    # === 假回答（本地模板，無外呼）===
    answer = f"根據已授權的文件回答：\n\n[{doc_id}] 這是文件內容示意。\n\n您的問題：{query}"

    # === Output：PII 去識別化（off 不做；report/enforce 會做）===
    answer, stats = guardrails.redact_pii(answer, mode)
    if stats:
        meta["redactions"] = sum(stats.values())
        for k, v in stats.items():
            if v > 0:
                REDACTIONS_TOTAL.labels(type=k).inc(v)

    # === Output：deny patterns（依 mode）===
    blocked, violations = guardrails.check_output(answer, mode)
    meta["violations"].extend(violations)
    if blocked:  # enforce 模式才會回 400
        meta["blocked"] = True
        REQUEST_COUNT.labels(route="/ask", method="POST").inc()
        REQUEST_BLOCKED.labels(route="/ask", method="POST", reason="output").inc()
        REQUEST_LATENCY.labels(route="/ask", method="POST").observe(time.time() - start_time)
        return JSONResponse(status_code=400, content={"answer": None, "meta": meta})

    # === Prometheus 記錄（成功路徑）===
    REQUEST_COUNT.labels(route="/ask", method="POST").inc()
    REQUEST_LATENCY.labels(route="/ask", method="POST").observe(time.time() - start_time)

    return JSONResponse(status_code=200, content={"answer": answer, "meta": meta})
