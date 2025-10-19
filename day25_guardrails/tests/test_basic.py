# test_basic.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    """最基本的測試：確認 app 能啟動"""
    # 如果你有 health check endpoint
    resp = client.get("/")
    # 或者測試任何簡單的 endpoint
    print(f"Status: {resp.status_code}")