from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

def test_ask():
    resp = client.post("/ask", json={"query": "如何設定公司 VPN？", "top_k": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert data["route"]["target"] in ("kb", "small_model")
    assert isinstance(data["contexts"], list)
