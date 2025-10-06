import os
import importlib
import pytest
from httpx import AsyncClient, ASGITransport

@pytest.mark.asyncio
async def test_happy_path(tmp_path, monkeypatch):
    # 1) 先設定獨立的 SQLite DB，再載入模組（避免抓到預設 registry.db）
    test_db = tmp_path / "test_registry.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{test_db}"

    import app.db as db
    importlib.reload(db)
    from app.main import app  # 這時 app 會用到剛設定的 DB
    db.init_db()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 建立模型
        r = await ac.post("/models", json={"name": "faq-bot", "owner": "hazel", "description": "Q&A bot"})
        assert r.status_code == 200
        assert r.json()["name"] == "faq-bot"

        # 建立 v1（預設 None）
        r = await ac.post("/models/faq-bot/versions", json={
            "version": "1.0.0",
            "artifact_url": "s3://bucket/faq-bot/1.0.0",
            "tags": ["baseline"],
            "meta": {"commit": "a1b2c3"}
        })
        assert r.status_code == 200
        assert r.json()["stage"] == "None"

        # None -> Staging -> Production
        r = await ac.post("/models/faq-bot/versions/1.0.0/transition", json={"to_stage": "Staging", "actor": "hazel"})
        assert r.status_code == 200 and r.json()["stage"] == "Staging"
        r = await ac.post("/models/faq-bot/versions/1.0.0/transition", json={"to_stage": "Production", "actor": "hazel"})
        assert r.status_code == 200 and r.json()["stage"] == "Production"

        # 建立 v2（預設 None）並升到 Staging（A/B 準備）
        r = await ac.post("/models/faq-bot/versions", json={
            "version": "1.1.0",
            "artifact_url": "s3://bucket/faq-bot/1.1.0",
            "tags": ["canary"],
            "meta": {"commit": "d4e5f6"}
        })
        assert r.status_code == 200 and r.json()["version"] == "1.1.0"
        r = await ac.post("/models/faq-bot/versions/1.1.0/transition", json={"to_stage": "Staging", "actor": "hazel"})
        assert r.status_code == 200 and r.json()["stage"] == "Staging"

        # Promote v2 -> Production（自動把 v1 降級為 Staging）
        r = await ac.post("/models/faq-bot/versions/1.1.0/transition", json={"to_stage": "Production", "actor": "hazel"})
        assert r.status_code == 200 and r.json()["stage"] == "Production"

        # 檢查唯一性：v1 應為 Staging、v2 為 Production
        r = await ac.get("/models/faq-bot/versions")
        versions = {v["version"]: v for v in r.json()}
        assert versions["1.0.0"]["stage"] == "Staging"
        assert versions["1.1.0"]["stage"] == "Production"

        # 回滾：把 v1 設回 Production（會自動把 v2 降回 Staging）
        r = await ac.post("/models/faq-bot/versions/1.0.0/transition",
                          json={"to_stage": "Production", "actor": "hazel", "rollback_to": True})
        assert r.status_code == 200 and r.json()["stage"] == "Production"

        # 封存 v2
        r = await ac.post("/models/faq-bot/versions/1.1.0/transition", json={"to_stage": "Archived", "actor": "hazel"})
        assert r.status_code == 200 and r.json()["stage"] == "Archived"

        # 目前 Production 應為 v1
        r = await ac.get("/models/faq-bot/production")
        assert r.status_code == 200 and r.json()["version"] == "1.0.0"
