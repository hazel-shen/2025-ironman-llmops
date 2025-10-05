from prometheus_client import Counter, Histogram, CollectorRegistry

from core.config import settings

registry = CollectorRegistry()

REQUEST_COUNTER = Counter(
    f"{settings.METRICS_NAMESPACE}_requests_total",
    "Total API requests",
    ["route"],
    registry=registry,
)

LATENCY_HISTOGRAM = Histogram(
    f"{settings.METRICS_NAMESPACE}_request_latency_seconds",
    "Request latency histogram",
    ["route"],
    buckets=(0.01, 0.03, 0.1, 0.3, 1, 3, 10),
    registry=registry,
)

CACHE_HIT_COUNTER = Counter(
    f"{settings.METRICS_NAMESPACE}_cache_hits_total",
    "Cache hits by kind",
    ["kind"],  # prompt | embed
    registry=registry,
)

CACHE_MISS_COUNTER = Counter(
    f"{settings.METRICS_NAMESPACE}_cache_miss_total",
    "Cache misses by kind",
    ["kind"],
    registry=registry,
)

TOKENS_PROMPT_COUNTER = Counter(
    f"{settings.METRICS_NAMESPACE}_tokens_prompt_total",
    "Prompt tokens total",
    registry=registry,
)

TOKENS_COMPLETION_COUNTER = Counter(
    f"{settings.METRICS_NAMESPACE}_tokens_completion_total",
    "Completion tokens total",
    registry=registry,
)

COST_USD_COUNTER = Counter(
    f"{settings.METRICS_NAMESPACE}_cost_usd_total",
    "Accumulative cost in USD",
    registry=registry,
)
