from fastapi.testclient import TestClient
from app.main import app

# 建立 FastAPI 測試用 client
client = TestClient(app)

def test_pii_redaction_in_answer():
    """
    測試情境：
    使用者在查詢中輸入了 Email 與手機號碼，
    系統應該依據 policy.yaml 的設定進行去識別化 (Redaction)，
    並將敏感資訊替換成 [REDACTED_EMAIL] 或 [REDACTED_PHONE]。
    """

    payload = {
        "query": "handbook 請寄到 my.mail+test@company.com 或 0912-345-678",
        "user": {"id": "u1", "role": "employee"}
    }

    # 呼叫 API /ask
    resp = client.post("/ask", json=payload)

    # 驗證 HTTP 狀態碼必須為 200 (成功處理)
    assert resp.status_code == 200, resp.text

    # 轉換成 JSON 方便檢查欄位
    data = resp.json()

    # 驗證回答中必須包含去識別化後的內容 (Email 或 Phone)
    assert "[REDACTED_EMAIL]" in data["answer"] or "[REDACTED_PHONE]" in data["answer"]

    # 驗證 meta.redactions 計數必須 >= 1 (確實有進行替換)
    assert data["meta"]["redactions"] >= 1

def test_api_key_redaction():
    """
    確認回覆若含有 OpenAI 金鑰 (sk-...)，會被遮罩。
    """
    payload = {
        "query": "這是一個測試，sk-abcdefghijklmnopqrstuvw12345",
        "user": {"id": "u1", "role": "employee"}
    }
    resp = client.post("/ask", json=payload)
    body = resp.json()
    assert "[REDACTED_APIKEY]" in body["answer"]
    assert body["meta"]["redactions"] > 0