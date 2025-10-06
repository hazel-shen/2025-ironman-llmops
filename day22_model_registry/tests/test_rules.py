import os
import importlib
import pytest
from httpx import AsyncClient, ASGITransport

@pytest.mark.asyncio
async def test_illegal_transitions_and_uniqueness(tmp_path):
    # 獨立 DB
    test_db = tmp_path / "test_registry_rules.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{test_db}"

    import app.db as db
    importlib.reload(db)
    from app.main import app
    db.init_db()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 建立模型
        r = await ac.post("/models", json={"name": "foo", "owner": "qa", "description": "rule tests"})
        assert r.status_code == 200

        # v1: None -> Staging -> Production
        assert (await ac.post("/models/foo/versions", json={"version": "1.0.0"})).status_code == 200
        assert (await ac.post("/models/foo/versions/1.0.0/transition", json={"to_stage": "Staging"})).status_code == 200
        assert (await ac.post("/models/foo/versions/1.0.0/transition", json={"to_stage": "Production"})).status_code == 200

        # v2: 建立（None）
        assert (await ac.post("/models/foo/versions", json={"version": "1.1.0"})).status_code == 200

        # 非法：None -> Production
        r = await ac.post("/models/foo/versions/1.1.0/transition", json={"to_stage": "Production"})
        assert r.status_code == 400
        assert "Illegal transition" in r.json()["detail"]

        # 合法：None -> Staging
        assert (await ac.post("/models/foo/versions/1.1.0/transition", json={"to_stage": "Staging"})).status_code == 200

        # 唯一性：把 v2 升到 Production，會自動把 v1 降到 Staging
        r = await ac.post("/models/foo/versions/1.1.0/transition", json={"to_stage": "Production"})
        assert r.status_code == 200

        r = await ac.get("/models/foo/versions")
        versions = {v["version"]: v for v in r.json()}
        assert versions["1.0.0"]["stage"] == "Staging"
        assert versions["1.1.0"]["stage"] == "Production"

        # 非法：Archived -> Production
        assert (await ac.post("/models/foo/versions/1.1.0/transition", json={"to_stage": "Archived"})).status_code == 200
        r = await ac.post("/models/foo/versions/1.1.0/transition", json={"to_stage": "Production"})
        assert r.status_code == 400
        assert "Illegal transition" in r.json()["detail"]
