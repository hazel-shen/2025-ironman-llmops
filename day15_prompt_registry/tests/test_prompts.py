# tests/test_prompts.py
import pytest

# ---- 規範：v1 FAQ (條列式) ----
def test_faq_v1_contains_core_instructions(reg):
    rendered = reg.render(
        "faq", "v1",
        context="VPN 文件路徑：/docs/vpn/setup",
        question="公司 VPN 怎麼設定？"
    )
    must_contains = [
        "你是一個專業客服助理",
        "【文件片段】",
        "【問題】",
        "僅引用文件內容，不要捏造",
        "文件中未提及",
        "VPN 文件路徑：/docs/vpn/setup",
        "公司 VPN 怎麼設定？",
    ]
    for m in must_contains:
        assert m in rendered

# ---- 規範：v2 FAQ (JSON 輸出) ----
def test_faq_v2_instructs_json_output(reg):
    rendered = reg.render(
        "faq", "v2",
        context="Some doc",
        question="Some question"
    )
    assert '"answer":' in rendered and '"citations":' in rendered
    assert "JSON" in rendered or "json" in rendered
    assert "不要自行捏造" in rendered or "僅能引用文件" in rendered

# ---- 規範：v1 Summary ----
def test_summary_v1_contains_three_bullets_instruction(reg):
    rendered = reg.render(
        "summary", "v1",
        context="公司創立於 2012 年，服務據點位於台北與新加坡。"
    )
    must_contains = [
        "總結為三點重點",
        "不超過 20 字",
        "公司創立於 2012 年",
    ]
    for m in must_contains:
        assert m in rendered

# ---- 規範：v2 Summary (JSON 條列) ----
def test_summary_v2_json_bullets_instruction(reg):
    rendered = reg.render(
        "summary", "v2",
        context="這是一段需要被總結的文字。"
    )
    assert '"bullets"' in rendered
    for i in ["第一點", "第二點", "第三點"]:
        assert i in rendered

# ---- 變數替換健全性檢查 ----
@pytest.mark.parametrize("name,version,vars_", [
    ("faq", "v1", {"context": "CTX", "question": "Q"}),
    ("faq", "v2", {"context": "CTX", "question": "Q"}),
    ("summary", "v1", {"context": "CTX"}),
    ("summary", "v2", {"context": "CTX"}),
])
def test_placeholders_are_filled(reg, name, version, vars_):
    rendered = reg.render(name, version, **vars_)
    assert "{{" not in rendered and "}}" not in rendered
