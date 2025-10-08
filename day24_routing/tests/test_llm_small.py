import pytest
from app.llm_small import answer_with_small_model
from app.models import ContextChunk

def test_answer_with_no_contexts():
    # 完全沒有命中 → 回退訊息
    ans, tokens, cost = answer_with_small_model("午餐補助怎麼領？", [])
    assert "沒有足夠線索" in ans
    assert tokens > 0
    assert cost == 0.0

def test_answer_with_zero_score_contexts():
    # contexts 全部 score=0 → 視為沒命中
    contexts = [
        ContextChunk(id="faq-001", text="公司 VPN 設定", score=0.0),
        ContextChunk(id="faq-002", text="請假流程", score=0.0),
    ]
    ans, tokens, cost = answer_with_small_model("午餐補助怎麼領？", contexts)
    assert "沒有足夠線索" in ans

def test_answer_with_valid_context():
    # 有分數的 context → 用知識庫拼接回答
    contexts = [
        ContextChunk(id="faq-001", text="公司 VPN 設定", score=0.5),
    ]
    ans, tokens, cost = answer_with_small_model("如何設定公司 VPN？", contexts)
    assert ans.startswith("根據知識庫：")
    assert "公司 VPN 設定" in ans
    assert tokens > 0
