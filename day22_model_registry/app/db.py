# app/db.py
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

# 允許透過環境變數覆蓋（方便測試）
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./registry.db")

# SQLite 要加 check_same_thread=False 才能在多線程下使用
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# ✅ 關鍵：避免 commit 後欄位被 expire，序列化時取值還在
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

def init_db() -> None:
    """建立資料表"""
    Base.metadata.create_all(bind=engine)

@contextmanager
def get_session():
    """取得 DB Session，並自動 commit/rollback"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
