from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class AskRequest(BaseModel):
    query: str = Field(..., description="User question")
    top_k: int = Field(3, ge=1, le=10, description="Retriever top-k")

class ContextChunk(BaseModel):
    id: str
    text: str
    score: float

class RetrievalSignals(BaseModel):
    max_score: float
    avg_topk: float
    num_docs: int
    context_len: int

class RouteDecision(BaseModel):
    target: Literal["kb", "small_model"]
    reason: str
    signals: RetrievalSignals

class AskResponse(BaseModel):
    answer: str
    route: RouteDecision
    contexts: List[ContextChunk]
    usage_tokens_est: Optional[int] = 0
    cost_usd_est: Optional[float] = 0.0
