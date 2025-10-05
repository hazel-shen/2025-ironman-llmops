# tests/test_metrics.py
import pytest
from core.config import settings

@pytest.mark.asyncio
async def test_metrics_and_json_updates(client, mock_llm, lower_threshold):
    # 打兩次 /ask 觸發計數
    await client.post("/ask", json={"question": "什麼是快取？"})
    await client.post("/ask", json={"question": "請解釋快取是什麼"})

    # 依設定動態組合 metric 名稱
    ns = settings.METRICS_NAMESPACE
    req_total = f"{ns}_requests_total"
    latency_hist = f"{ns}_request_latency_seconds"
    hits_total = f"{ns}_cache_hits_total"
    miss_total = f"{ns}_cache_miss_total"
    tokens_prompt = f"{ns}_tokens_prompt_total"
    tokens_completion = f"{ns}_tokens_completion_total"
    cost_total = f"{ns}_cost_usd_total"

    # Prometheus 文字格式檢查
    m = await client.get("/metrics")
    assert m.status_code == 200
    text = m.text

    # 關鍵 metrics 名稱存在
    for key in [req_total, latency_hist, hits_total, miss_total, tokens_prompt, tokens_completion, cost_total]:
        assert key in text, f"missing {key} in /metrics output"

    # JSON metrics 應該 > 0
    j = await client.get("/metrics/json")
    assert j.status_code == 200
    data = j.json()

    # 至少有請求與部分 cache 統計欄位
    assert data["requests"] >= 2
    assert "prompt" in data["cache_hits"] and "embed" in data["cache_hits"]
    assert "prompt" in data["cache_miss"] and "embed" in data["cache_miss"]

    # 允許兩種情況：prompt 或 embed 至少有一者命中
    assert (data["cache_hits"]["prompt"] > 0) or (data["cache_hits"]["embed"] > 0)
