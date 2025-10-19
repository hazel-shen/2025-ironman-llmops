# test_simple_request.py
from fastapi.testclient import TestClient
from app.main import app
import signal

client = TestClient(app)

def timeout_handler(signum, frame):
    raise TimeoutError("測試超時！")

def test_simple_query():
    """測試最簡單的正常請求"""
    # 設定 5 秒超時
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(5)
    
    try:
        payload = {
            "query": "test",
            "user": {"id": "u1", "role": "employee"}
        }
        print("\n[DEBUG] 發送請求...")
        resp = client.post("/ask", json=payload)
        print(f"[DEBUG] 狀態碼: {resp.status_code}")
        print(f"[DEBUG] 回應: {resp.text[:200]}")
        
        assert resp.status_code in (200, 400, 403)
    finally:
        signal.alarm(0)  # 取消超時