# test_redact_pii.py
"""測試 Guardrails.redact_pii 方法"""
import pytest
from app.guardrails import Guardrails


class TestRedactPII:
    """測試 PII 去識別化功能"""
    
    @pytest.fixture
    def policy_with_email_phone(self):
        """包含 email 和 phone 的 policy"""
        return {
            "pii": {
                "redact": ["email", "phone"]
            },
            "io_limit": {
                "max_input_length": 1000,
                "max_output_length": 500
            }
        }
    
    @pytest.fixture
    def policy_email_only(self):
        """只遮罩 email 的 policy"""
        return {
            "pii": {
                "redact": ["email"]
            },
            "io_limit": {
                "max_input_length": 1000,
                "max_output_length": 500
            }
        }
    
    @pytest.fixture
    def policy_phone_only(self):
        """只遮罩 phone 的 policy"""
        return {
            "pii": {
                "redact": ["phone"]
            },
            "io_limit": {
                "max_input_length": 1000,
                "max_output_length": 500
            }
        }
    
    def test_mode_off_no_redaction(self, policy_with_email_phone):
        """測試 off 模式：不遮罩任何內容"""
        gr = Guardrails(policy_with_email_phone)
        text = "Contact me at test@example.com or 0912-345-678"
        result, stats = gr.redact_pii(text, mode="off")
        assert result == text  # 完全不變
        assert stats == {}  # 沒有統計
    
    def test_redact_email(self, policy_with_email_phone):
        """測試遮罩 email"""
        gr = Guardrails(policy_with_email_phone)
        text = "My email is john.doe@company.com"
        result, stats = gr.redact_pii(text, mode="enforce")
        assert "[REDACTED_EMAIL]" in result
        assert "john.doe@company.com" not in result
        assert stats.get("email", 0) == 1
    
    def test_redact_multiple_emails(self, policy_with_email_phone):
        """測試遮罩多個 email"""
        gr = Guardrails(policy_with_email_phone)
        text = "Contacts: alice@test.com and bob@example.org"
        result, stats = gr.redact_pii(text, mode="enforce")
        assert result.count("[REDACTED_EMAIL]") == 2
        assert stats.get("email", 0) == 2
    
    def test_redact_taiwan_phone_with_dash(self, policy_with_email_phone):
        """測試遮罩台灣手機號碼（有破折號）"""
        gr = Guardrails(policy_with_email_phone)
        text = "Call me at 0912-345-678"
        result, stats = gr.redact_pii(text, mode="enforce")
        assert "[REDACTED_PHONE]" in result
        assert "0912-345-678" not in result
        assert stats.get("phone", 0) >= 1
    
    def test_redact_taiwan_phone_no_dash(self, policy_with_email_phone):
        """測試遮罩台灣手機號碼（無破折號）"""
        gr = Guardrails(policy_with_email_phone)
        text = "My phone is 0987654321"
        result, stats = gr.redact_pii(text, mode="enforce")
        assert "[REDACTED_PHONE]" in result
        assert "0987654321" not in result
        assert stats.get("phone", 0) >= 1
    
    def test_redact_international_phone(self, policy_with_email_phone):
        """測試遮罩國際電話號碼"""
        gr = Guardrails(policy_with_email_phone)
        text = "International: +886-2-1234-5678"
        result, stats = gr.redact_pii(text, mode="enforce")
        assert "[REDACTED_PHONE]" in result
        assert stats.get("phone", 0) >= 1
    
    def test_redact_api_key(self, policy_with_email_phone):
        """測試遮罩 API 金鑰"""
        gr = Guardrails(policy_with_email_phone)
        text = "My key is sk-abcdefghijklmnopqrst123456"
        result, stats = gr.redact_pii(text, mode="enforce")
        assert "[REDACTED_APIKEY]" in result
        assert "sk-abc" not in result
        assert stats.get("apikey", 0) == 1
    
    def test_no_pii_in_text(self, policy_with_email_phone):
        """測試沒有 PII 的文字"""
        gr = Guardrails(policy_with_email_phone)
        text = "This is a clean text without any sensitive data"
        result, stats = gr.redact_pii(text, mode="enforce")
        assert result == text
        assert stats.get("email", 0) == 0
        assert stats.get("phone", 0) == 0
    
    def test_email_only_policy(self, policy_email_only):
        """測試只遮罩 email 的 policy"""
        gr = Guardrails(policy_email_only)
        text = "Email: test@example.com Phone: 0912-345-678"
        result, stats = gr.redact_pii(text, mode="enforce")
        assert "[REDACTED_EMAIL]" in result
        assert "[REDACTED_PHONE]" not in result  # phone 不應被遮罩
        assert "0912-345-678" in result  # phone 保留
    
    def test_phone_only_policy(self, policy_phone_only):
        """測試只遮罩 phone 的 policy"""
        gr = Guardrails(policy_phone_only)
        text = "Email: test@example.com Phone: 0912-345-678"
        result, stats = gr.redact_pii(text, mode="enforce")
        assert "[REDACTED_PHONE]" in result
        assert "[REDACTED_EMAIL]" not in result  # email 不應被遮罩
        assert "test@example.com" in result  # email 保留
    
    def test_truncate_long_input(self, policy_with_email_phone):
        """測試超長輸入會被截斷"""
        gr = Guardrails(policy_with_email_phone)
        long_text = "a" * 2000  # 超過 max_input_length
        result, stats = gr.redact_pii(long_text, mode="enforce")
        assert len(result) == 1000  # 被截斷到 max_input_length
        assert stats.get("truncated") is True
    
    def test_empty_text(self, policy_with_email_phone):
        """測試空文字"""
        gr = Guardrails(policy_with_email_phone)
        result, stats = gr.redact_pii("", mode="enforce")
        assert result == ""
        assert stats.get("email", 0) == 0
    
    def test_none_text(self, policy_with_email_phone):
        """測試 None 輸入"""
        gr = Guardrails(policy_with_email_phone)
        result, stats = gr.redact_pii(None, mode="enforce")
        assert result == ""
        assert stats.get("email", 0) == 0