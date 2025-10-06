from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

# --- Model ---
class ModelCreate(BaseModel):
    name: str
    owner: Optional[str] = None
    description: Optional[str] = None


class ModelOut(BaseModel):
    id: int
    name: str
    owner: Optional[str]
    description: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True


# --- Version ---
class VersionCreate(BaseModel):
    version: str
    artifact_url: Optional[str] = None
    tags: List[str] = []
    meta: dict = {}


class VersionOut(BaseModel):
    id: int
    version: str
    stage: str
    artifact_url: Optional[str]
    tags: List[str]
    meta: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# --- Audit ---
class AuditOut(BaseModel):
    id: int
    model_name: str
    version: Optional[str]
    action: str
    actor: Optional[str]
    from_stage: Optional[str]
    to_stage: Optional[str]
    detail: dict
    created_at: datetime

    class Config:
        orm_mode = True
