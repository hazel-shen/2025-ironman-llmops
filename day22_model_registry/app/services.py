from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import Model, ModelVersion, Audit
from .utils import can_transition

class RegistryService:
    def __init__(self, session: Session):
        self.session = session

    # --- Model ---
    def create_model(self, name: str, owner: Optional[str], description: Optional[str]):
        existing = self.session.scalar(select(Model).where(Model.name == name))
        if existing:
            return existing
        m = Model(name=name, owner=owner, description=description)
        self.session.add(m)
        self._audit("create_model", name, None, actor=owner, detail={"description": description})
        return m

    def list_models(self) -> List[Model]:
        return list(self.session.scalars(select(Model)).all())

    # --- Version ---
    def create_version(self, model_name: str, version: str, artifact_url: Optional[str], tags: list, meta: dict):
        model = self.session.scalar(select(Model).where(Model.name == model_name))
        if not model:
            raise ValueError(f"Model {model_name} not found")
        if self.session.scalar(
            select(ModelVersion).where(
                ModelVersion.model_id == model.id,
                ModelVersion.version == version,
            )
        ):
            raise ValueError("Version already exists")
        v = ModelVersion(model_id=model.id, version=version, artifact_url=artifact_url, tags=tags, meta=meta)
        self.session.add(v)
        self._audit("create_version", model_name, version, detail={"artifact_url": artifact_url, "tags": tags, "meta": meta})
        return v

    def list_versions(self, model_name: str) -> List[ModelVersion]:
        model = self.session.scalar(select(Model).where(Model.name == model_name))
        if not model:
            raise ValueError(f"Model {model_name} not found")
        return list(self.session.scalars(select(ModelVersion).where(ModelVersion.model_id == model.id)).all())

    def current_production(self, model_name: str) -> Optional[ModelVersion]:
        model = self.session.scalar(select(Model).where(Model.name == model_name))
        if not model:
            return None
        return self.session.scalar(
            select(ModelVersion).where(
                ModelVersion.model_id == model.id, ModelVersion.stage == "Production"
            )
        )

    # --- Transition ---
    def transition(self, model_name: str, version: str, to_stage: str, actor: Optional[str], rollback_to: bool = False) -> ModelVersion:
        model = self.session.scalar(select(Model).where(Model.name == model_name))
        if not model:
            raise ValueError(f"Model {model_name} not found")
        v = self.session.scalar(select(ModelVersion).where(ModelVersion.model_id == model.id, ModelVersion.version == version))
        if not v:
            raise ValueError("Version not found")
        if not can_transition(v.stage, to_stage):
            raise ValueError(f"Illegal transition {v.stage} → {to_stage}")

        # Enforce single Production per model by auto-downgrading the previous Production
        if to_stage == "Production":
            prev = self.session.scalar(
                select(ModelVersion).where(
                    ModelVersion.model_id == model.id,
                    ModelVersion.stage == "Production",
                )
            )
            if prev and prev.version != v.version:
                prev.stage = "Staging"

        old = v.stage
        v.stage = to_stage
        self._audit("transition", model_name, v.version, actor=actor, from_stage=old, to_stage=to_stage, detail={"rollback_to": rollback_to})
        return v

    # --- Audit ---
    def list_audit(self) -> List[Audit]:
        return list(self.session.scalars(select(Audit)).all())

    def _audit(
        self,
        action: str,
        model_name: str,
        version: Optional[str],
        actor: Optional[str] = None,
        from_stage: Optional[str] = None,
        to_stage: Optional[str] = None,
        detail: Optional[dict] = None,
    ):
        a = Audit(
            action=action,
            model_name=model_name,
            version=version,
            actor=actor,
            from_stage=from_stage,
            to_stage=to_stage,
            detail=detail or {},
        )
        self.session.add(a)
