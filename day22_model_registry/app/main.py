# app/main.py
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .db import get_session, init_db
from .services import RegistryService
from .schemas import (
    ModelCreate, ModelOut,
    VersionCreate, VersionOut,
    AuditOut,
)

app = FastAPI(title="Model Registry Demo")


# 啟動時建立資料表
@app.on_event("startup")
def _startup():
    init_db()


@app.get("/healthz")
def healthz():
    return {"ok": True}


# ===== Models =====

@app.post("/models", response_model=ModelOut)
def create_model(body: ModelCreate):
    with get_session() as s:
        svc = RegistryService(s)
        try:
            m = svc.create_model(body.name, body.owner, body.description)
            s.flush(); s.refresh(m)
            return m
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@app.get("/models", response_model=List[ModelOut])
def list_models():
    with get_session() as s:
        svc = RegistryService(s)
        return svc.list_models()


# ===== Versions =====

@app.post("/models/{name}/versions", response_model=VersionOut)
def create_version(name: str, body: VersionCreate):
    with get_session() as s:
        svc = RegistryService(s)
        try:
            v = svc.create_version(name, body.version, body.artifact_url, body.tags, body.meta)
            s.flush(); s.refresh(v)
            return v
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


@app.get("/models/{name}/versions", response_model=List[VersionOut])
def list_versions(name: str):
    with get_session() as s:
        svc = RegistryService(s)
        try:
            return svc.list_versions(name)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))


@app.get("/models/{name}/production", response_model=VersionOut)
def get_current_production(name: str):
    with get_session() as s:
        svc = RegistryService(s)
        v = svc.current_production(name)
        if not v:
            raise HTTPException(status_code=404, detail="No production version")
        return v


# 轉換的請求模型（用簡單字串即可，服務層會驗證是否合法）
class TransitionIn(BaseModel):
    to_stage: str
    actor: Optional[str] = None
    rollback_to: bool = False


@app.post("/models/{name}/versions/{version}/transition", response_model=VersionOut)
def transition(name: str, version: str, body: TransitionIn):
    with get_session() as s:
        svc = RegistryService(s)
        try:
            v = svc.transition(
                model_name=name,
                version=version,
                to_stage=body.to_stage,
                actor=body.actor,
                rollback_to=body.rollback_to,
            )
            s.flush(); s.refresh(v)
            return v
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


# ===== Audit =====

@app.get("/audit", response_model=List[AuditOut])
def list_audit():
    with get_session() as s:
        svc = RegistryService(s)
        return svc.list_audit()
