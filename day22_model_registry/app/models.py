import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, JSON, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Stage(str, enum.Enum):
    none = "None"
    staging = "Staging"
    production = "Production"
    archived = "Archived"


class Model(Base):
    __tablename__ = "models"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    owner = Column(String, nullable=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    versions = relationship(
        "ModelVersion", back_populates="model", cascade="all, delete-orphan"
    )


class ModelVersion(Base):
    __tablename__ = "model_versions"
    id = Column(Integer, primary_key=True)
    model_id = Column(Integer, ForeignKey("models.id"), index=True)
    version = Column(String, nullable=False)
    stage = Column(String, default=Stage.none.value, nullable=False) # 以字串存到 DB，預設為 "None"
    artifact_url = Column(String, nullable=True)
    tags = Column(JSON, default=list)
    meta = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    model = relationship("Model", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("model_id", "version", name="uq_model_version"),
    )


class Audit(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    model_name = Column(String, index=True)
    version = Column(String, nullable=True)
    action = Column(String)  # create_model / create_version / transition
    actor = Column(String, nullable=True)
    from_stage = Column(String, nullable=True)
    to_stage = Column(String, nullable=True)
    detail = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
