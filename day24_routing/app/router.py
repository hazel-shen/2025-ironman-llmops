# app/router.py
import os
from .models import RetrievalSignals, RouteDecision

THRESH_MAX = float(os.getenv("ROUTER_THRESH_MAX", "0.30"))
THRESH_AVG = float(os.getenv("ROUTER_THRESH_AVG", "0.12"))
MIN_DOCS   = int(os.getenv("ROUTER_MIN_DOCS", "1"))

def decide(signals: RetrievalSignals) -> RouteDecision:
    go_kb = (
        (signals.max_score >= THRESH_MAX or signals.avg_topk >= THRESH_AVG)
        and signals.num_docs >= MIN_DOCS
    )
    target = "kb" if go_kb else "small_model"
    reason = (
        f"max={signals.max_score:.2f} avg={signals.avg_topk:.2f} "
        f"docs={signals.num_docs} → {target}"
    )
    return RouteDecision(target=target, reason=reason, signals=signals)
