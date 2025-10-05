import time
from typing import Dict, Optional
from prometheus_client.samples import Sample
from fastapi import APIRouter, HTTPException
from core.config import settings
from core.metrics import (
    REQUEST_COUNTER,
    LATENCY_HISTOGRAM,
    CACHE_HIT_COUNTER,
    CACHE_MISS_COUNTER,
    TOKENS_PROMPT_COUNTER,
    TOKENS_COMPLETION_COUNTER,
    COST_USD_COUNTER,
    registry,
)
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import PlainTextResponse
from models.schemas import AskRequest, AskResponse, MetricsJSON
from services.cache import PromptCache
from services.embed_cache_redis import EmbeddingCacheRedis
from services.llm import LLMService

router = APIRouter(tags=["ask"])

prompt_cache = PromptCache()
llm = LLMService()
embed_cache = EmbeddingCacheRedis(dim=settings.EMBED_CACHE_DIM, embed_fn=llm.embed)

@router.post("/ask", response_model=AskResponse)
async def ask(payload: AskRequest):
    start = time.perf_counter()
    REQUEST_COUNTER.labels(route="/ask").inc()

    # 1) Prompt Cache（精確字串）
    cached = await prompt_cache.get(payload.question)
    if cached is not None:
        CACHE_HIT_COUNTER.labels(kind="prompt").inc()
        LATENCY_HISTOGRAM.labels(route="/ask").observe(time.perf_counter() - start)
        return AskResponse(
            question=payload.question,
            answer=cached["answer"],
            source=cached["source"],
            prompt_tokens=cached.get("prompt_tokens", 0),
            completion_tokens=cached.get("completion_tokens", 0),
            cost_usd=cached.get("cost_usd", 0.0),
            cache_hit=True
        )

    CACHE_MISS_COUNTER.labels(kind="prompt").inc()

    # 2) Embedding Cache（語意近似）
    if settings.ENABLE_EMBED_CACHE:
        near = await embed_cache.search_similar(payload.question, threshold=settings.EMBED_SIM_THRESHOLD)
        if near is not None:
            CACHE_HIT_COUNTER.labels(kind="embed").inc()
            LATENCY_HISTOGRAM.labels(route="/ask").observe(time.perf_counter() - start)
            return AskResponse(
                question=payload.question,
                answer=near["answer"],
                source="embed_cache",
                prompt_tokens=near.get("prompt_tokens", 0),
                completion_tokens=near.get("completion_tokens", 0),
                cost_usd=near.get("cost_usd", 0.0),
                cache_hit=True
            )
    else:
        CACHE_MISS_COUNTER.labels(kind="embed").inc()

    # 3) 真正呼叫 LLM
    try:
        result = await llm.chat(payload.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")

    # 更新 metrics
    TOKENS_PROMPT_COUNTER.inc(result.prompt_tokens)
    TOKENS_COMPLETION_COUNTER.inc(result.completion_tokens)
    COST_USD_COUNTER.inc(result.cost_usd or 0.0)

    # 4) 回寫快取
    await prompt_cache.set(
        payload.question,
        {
            "answer": result.answer,
            "source": "llm",
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "cost_usd": result.cost_usd or 0.0
        },
        ttl=settings.CACHE_TTL,
    )
    if settings.ENABLE_EMBED_CACHE:
        await embed_cache.upsert(payload.question, result.answer, {
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "cost_usd": result.cost_usd or 0.0
        })

    LATENCY_HISTOGRAM.labels(route="/ask").observe(time.perf_counter() - start)

    return AskResponse(
        question=payload.question,
        answer=result.answer,
        source="llm",
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        cost_usd=result.cost_usd or 0.0,
        cache_hit=False
    )

@router.get("/metrics", response_class=PlainTextResponse)
def metrics():
    data = generate_latest(registry)
    return PlainTextResponse(content=data, media_type=CONTENT_TYPE_LATEST)

# JSON metrics（方便人類看）
def _sum_counter_total(counter) -> float:
    """合計一個 Counter 的所有 *_total 樣本值（忽略 labels）。"""
    total = 0.0
    for metric in counter.collect():
        for s in metric.samples:
            if s.name.endswith("_total"):
                total += float(s.value or 0)
    return total

def _sum_counter_total_with_labels(counter, match_labels: Dict[str, str]) -> float:
    """合計一個帶 labels 的 Counter 在特定 labels 下的 *_total 值。"""
    total = 0.0
    for metric in counter.collect():
        for s in metric.samples:
            if not s.name.endswith("_total"):
                continue
            labels = s.labels or {}
            if all(labels.get(k) == v for k, v in match_labels.items()):
                total += float(s.value or 0)
    return total

@router.get("/metrics/json", response_model=MetricsJSON)
def metrics_json():
    # requests (所有 route 加總)
    requests_total = _sum_counter_total(REQUEST_COUNTER)

    # cache hits / miss（依 kind 區分）
    hit_prompt  = _sum_counter_total_with_labels(CACHE_HIT_COUNTER,  {"kind": "prompt"})
    hit_embed   = _sum_counter_total_with_labels(CACHE_HIT_COUNTER,  {"kind": "embed"})
    miss_prompt = _sum_counter_total_with_labels(CACHE_MISS_COUNTER, {"kind": "prompt"})
    miss_embed  = _sum_counter_total_with_labels(CACHE_MISS_COUNTER, {"kind": "embed"})

    return MetricsJSON(
        requests=requests_total,
        cache_hits={"prompt": hit_prompt, "embed": hit_embed},
        cache_miss={"prompt": miss_prompt, "embed": miss_embed},
    )

