from prometheus_client import Counter, Histogram

REQUESTS_TOTAL = Counter(
    "gateway_requests_total", "Total API requests", ["route"]
)
REQUEST_BLOCKED_TOTAL = Counter(
    "gateway_requests_blocked_total", "Requests blocked by guardrails", ["reason"]
)
REDACTIONS_TOTAL = Counter(
    "gateway_redactions_total", "Total redactions performed", ["type"]
)
ACL_DENIED_TOTAL = Counter(
    "gateway_acl_denied_total", "Total retrieval ACL denials", ["doc_id"]
)
REQUEST_LATENCY = Histogram(
    "gateway_request_latency_seconds", "Request latency histogram", ["route"],
    buckets=(0.01, 0.03, 0.1, 0.3, 1, 3, 10)
)
