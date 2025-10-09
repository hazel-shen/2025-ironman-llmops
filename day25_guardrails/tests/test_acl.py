from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_acl_denied_for_finance_doc():
    """
    情境：
    employee 嘗試存取 finance 文件，應該被拒絕 (403)。
    """
    payload = {
        "query": "請提供 finance 報銷規範",
        "user": {"id": "u2", "role": "employee"}  # employee 不可讀 finance
    }
    resp = client.post("/ask", json=payload)
    assert resp.status_code == 403
    data = resp.json()
    # 驗證被擋下
    assert data["meta"]["blocked"] is True
    # 驗證 violations 有正確紀錄
    assert "acl_denied:doc_finance" in data["meta"]["violations"]


def test_acl_allowed_for_admin():
    """
    情境：
    admin 嘗試存取 finance 文件，應該允許。
    """
    payload = {
        "query": "finance 報銷怎麼走？",
        "user": {"id": "admin", "role": "admin"}
    }
    resp = client.post("/ask", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # 驗證檢索到的文件包含 doc_finance
    assert "doc_finance" in data["meta"]["retrieved_docs"]
