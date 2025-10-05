from pydantic import BaseModel

class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    question: str
    answer: str
    source: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float | None = 0.0
    cache_hit: bool = False

class MetricsJSON(BaseModel):
    requests: float
    cache_hits: dict
    cache_miss: dict
