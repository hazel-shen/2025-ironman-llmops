import time
from typing import Callable, Any, Dict
from prometheus_client import Counter, Histogram

REQUESTS = Counter("day24_requests_total", "Total /ask requests")
ROUTE_DECISION = Counter("day24_route_decision_total", "Routing target", ["target"])
TOKENS = Counter("day24_tokens_total", "Estimated tokens used", ["role"])  # role: prompt|completion
COST = Counter("day24_cost_usd_total", "Estimated USD cost")
LATENCY = Histogram(
    "day24_request_latency_seconds",
    "Request latency",
    buckets=(0.01, 0.03, 0.1, 0.3, 1, 3, 10)
)

def track_request(func: Callable[..., Any]):
    def wrapper(*args, **kwargs):
        REQUESTS.inc()
        start = time.perf_counter()
        try:
            res: Dict[str, Any] = func(*args, **kwargs)
            return res
        finally:
            LATENCY.observe(time.perf_counter() - start)
    return wrapper
