import pytest

@pytest.mark.asyncio
async def test_api_prompt_cache_hit(client, mock_llm):
    # 第一次：走 LLM
    r1 = await client.post("/ask", json={"question": "什麼是快取？"})
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["cache_hit"] is False
    assert d1["source"] == "llm"
    assert d1["answer"].startswith("[fake answer]")

    # 第二次同問：命中 Prompt Cache
    r2 = await client.post("/ask", json={"question": "什麼是快取？"})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["cache_hit"] is True
    # 來源仍會是 "llm"（因為是第一次寫入的來源），重點是 cache_hit=True
    assert "answer" in d2


@pytest.mark.asyncio
async def test_api_embed_cache_hit(client, mock_llm, lower_threshold):
    # 第一次問題：寫入語意快取
    r1 = await client.post("/ask", json={"question": "什麼是快取？"})
    assert r1.status_code == 200

    # 第二次相似問法：命中語意快取（mock embed → 相似度=1）
    r2 = await client.post("/ask", json={"question": "請解釋快取是什麼"})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["cache_hit"] is True
    assert d2["source"] in ("embed_cache", "llm")  # 在某些實作先命中 prompt 也可接受
    assert "answer" in d2
