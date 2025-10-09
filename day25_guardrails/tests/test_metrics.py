from fastapi.testclient import TestClient
from app.main import app

# 建立 FastAPI 測試用 client
client = TestClient(app)

def test_metrics_exposed():
    """
    測試情境：
    驗證 /metrics 端點是否正確暴露 Prometheus 指標，
    並且包含 gateway_requests_total 與 gateway_request_latency_seconds。
    """

    # 呼叫 /metrics
    resp = client.get("/metrics")

    # 驗證 HTTP 狀態碼必須為 200 (成功)
    assert resp.status_code == 200

    # 取得回傳內容 (純文字格式)
    text = resp.text

    # 驗證是否包含主要的計數器與直方圖指標
    assert "gateway_requests_total" in text
    assert "gateway_request_latency_seconds" in text
