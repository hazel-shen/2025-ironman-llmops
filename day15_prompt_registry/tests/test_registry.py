# tests/test_registry.py
import pytest
from registry.registry import PromptRegistry

def test_list_versions_contains_v1_v2(reg: PromptRegistry):
    versions = reg.list_versions()
    assert "v1" in versions
    assert "v2" in versions

@pytest.mark.parametrize("version", ["v1", "v2"])
def test_list_prompts_has_faq_and_summary(reg: PromptRegistry, version: str):
    names = reg.list_prompts(version)
    assert "faq" in names
    assert "summary" in names

@pytest.mark.parametrize("name,version,vars_", [
    ("faq", "v1", {"context": "A", "question": "Q?"}),
    ("faq", "v2", {"context": "A", "question": "Q?"}),
    ("summary", "v1", {"context": "Some text"}),
    ("summary", "v2", {"context": "Some text"}),
])
def test_get_and_render_returns_string(reg: PromptRegistry, name, version, vars_):
    template = reg.get(name, version)
    assert isinstance(template, str) and len(template) > 0

    rendered = reg.render(name, version, **vars_)
    assert isinstance(rendered, str) and len(rendered) > 0
    assert "{{" not in rendered and "}}" not in rendered

def test_missing_prompt_raises_keyerror(reg: PromptRegistry):
    with pytest.raises(KeyError):
        reg.get("not_exist_prompt", "v1")

def test_missing_version_raises_keyerror(reg: PromptRegistry):
    with pytest.raises(KeyError):
        reg.get("faq", "v999")

def test_render_without_required_vars_still_string(reg: PromptRegistry):
    rendered = reg.render("faq", "v1")  # 少帶 context/question
    assert isinstance(rendered, str)
