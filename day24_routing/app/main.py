import os
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from .models import AskRequest, AskResponse
from .retriever import SimpleRetriever
from .router import decide
from .llm_small import answer_with_small_model
from .metrics import track_request, ROUTE_DECISION, TOKENS, COST

KB_PATH = os.getenv("KB_PATH", "data/kb.jsonl")

app = FastAPI(title="Day24 Routing Demo", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

retriever = SimpleRetriever(KB_PATH)

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@track_request
@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    contexts, signals = retriever.search(req.query, top_k=req.top_k)
    route = decide(signals)

    if route.target == "kb" and contexts:
        # 直接用 KB 第一名回覆（demo）
        answer = contexts[0].text
        usage_tokens_est = int(len(req.query) / 4 + len(answer) / 4)
        cost_usd_est = 0.0  # KB 回覆假設不花 API 費
    else:
        answer, tokens, cost = answer_with_small_model(req.query, contexts)
        usage_tokens_est = tokens
        cost_usd_est = cost

    ROUTE_DECISION.labels(route.target).inc()
    TOKENS.labels("prompt").inc(int(len(req.query) / 4))
    TOKENS.labels("completion").inc(int(len(answer) / 4))
    COST.inc(cost_usd_est)

    return AskResponse(
        answer=answer,
        route=route,
        contexts=contexts,
        usage_tokens_est=usage_tokens_est,
        cost_usd_est=cost_usd_est,
    )
