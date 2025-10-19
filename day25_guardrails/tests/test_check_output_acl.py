# test_check_output_acl.py
"""測試 Guardrails.check_output 和 enforce_acl 方法"""
import pytest
from app.guardrails import Guardrails


class TestCheckOutput:
    """測試 check_output 方法"""
    
    @pytest.fixture
    def policy(self):
        """測試用的 policy 配置"""
        return {
            "output": {
                "deny_patterns": [
                    r"(?i)confidential",
                    r"(?i)internal\s+only",
                    r"password:\s*\S+",
                ]
            },
            "io_limit": {
                "max_input_length": 1000,
                "max_output_length": 500
            }
        }
    
    @pytest.fixture
    def guardrails(self, policy):
        """建立 Guardrails 實例"""
        return Guardrails(policy)
    
    def test_mode_off_no_check(self, guardrails):
        """測試 off 模式：不檢查輸出"""
        text = "This is CONFIDENTIAL information"
        blocked, violations = guardrails.check_output(text, mode="off")
        assert blocked is False
        assert violations == []
    
    def test_mode_enforce_block_confidential(self, guardrails):
        """測試 enforce 模式：阻擋機密資訊"""
        text = "This document is CONFIDENTIAL"
        blocked, violations = guardrails.check_output(text, mode="enforce")
        assert blocked is True
        assert len(violations) > 0
        assert any("confidential" in v.lower() for v in violations)
    
    def test_mode_enforce_block_internal_only(self, guardrails):
        """測試 enforce 模式：阻擋 internal only"""
        text = "This is INTERNAL ONLY data"
        blocked, violations = guardrails.check_output(text, mode="enforce")
        assert blocked is True
        assert len(violations) > 0
    
    def test_mode_enforce_block_password(self, guardrails):
        """測試 enforce 模式：阻擋密碼外洩"""
        text = "Your password: abc123xyz"
        blocked, violations = guardrails.check_output(text, mode="enforce")
        assert blocked is True
        assert len(violations) > 0
    
    def test_mode_report_detect_not_block(self, guardrails):
        """測試 report 模式：偵測但不阻擋"""
        text = "This is CONFIDENTIAL"
        blocked, violations = guardrails.check_output(text, mode="report")
        assert blocked is False  # report 模式不阻擋
        assert len(violations) > 0  # 但會記錄違規
    
    def test_clean_output_no_violation(self, guardrails):
        """測試乾淨輸出：沒有違規"""
        text = "This is a normal response"
        blocked, violations = guardrails.check_output(text, mode="enforce")
        assert blocked is False
        assert violations == []
    
    def test_empty_output(self, guardrails):
        """測試空輸出"""
        blocked, violations = guardrails.check_output("", mode="enforce")
        assert blocked is False
        assert violations == []
    
    def test_none_output(self, guardrails):
        """測試 None 輸出"""
        blocked, violations = guardrails.check_output(None, mode="enforce")
        assert blocked is False
        assert violations == []
    
    def test_multiple_violations(self, guardrails):
        """測試多個違規規則"""
        text = "CONFIDENTIAL: INTERNAL ONLY password: secret123"
        blocked, violations = guardrails.check_output(text, mode="report")
        assert blocked is False  # report 模式
        assert len(violations) >= 2  # 至少兩個違規


class TestEnforceACL:
    """測試 enforce_acl 方法"""
    
    @pytest.fixture
    def policy(self):
        """測試用的 ACL policy"""
        return {
            "retrieval": {
                "docs": {
                    "doc_public": {
                        "roles": ["employee", "admin", "guest"]
                    },
                    "doc_finance": {
                        "roles": ["admin", "finance"]
                    },
                    "doc_hr": {
                        "roles": ["admin", "hr"]
                    },
                    "doc_tech": {
                        "roles": ["admin", "engineer"]
                    }
                }
            },
            "io_limit": {
                "max_input_length": 1000,
                "max_output_length": 500
            }
        }
    
    @pytest.fixture
    def guardrails(self, policy):
        """建立 Guardrails 實例"""
        return Guardrails(policy)
    
    def test_mode_off_allow_all(self, guardrails):
        """測試 off 模式：允許所有存取"""
        allowed, violations = guardrails.enforce_acl(
            user_role="guest",
            doc_ids=["doc_finance", "doc_hr"],
            mode="off"
        )
        assert allowed is True
        assert violations == []
    
    def test_admin_access_all_docs(self, guardrails):
        """測試 admin 可以存取所有文件"""
        allowed, violations = guardrails.enforce_acl(
            user_role="admin",
            doc_ids=["doc_finance", "doc_hr", "doc_tech"],
            mode="enforce"
        )
        assert allowed is True
        assert violations == []
    
    def test_employee_access_public_only(self, guardrails):
        """測試 employee 只能存取 public 文件"""
        allowed, violations = guardrails.enforce_acl(
            user_role="employee",
            doc_ids=["doc_public"],
            mode="enforce"
        )
        assert allowed is True
        assert violations == []
    
    def test_employee_denied_finance(self, guardrails):
        """測試 employee 被拒絕存取 finance 文件"""
        allowed, violations = guardrails.enforce_acl(
            user_role="employee",
            doc_ids=["doc_finance"],
            mode="enforce"
        )
        assert allowed is False
        assert len(violations) > 0
        assert "acl_denied:doc_finance" in violations
    
    def test_finance_role_access_finance_doc(self, guardrails):
        """測試 finance 角色可以存取 finance 文件"""
        allowed, violations = guardrails.enforce_acl(
            user_role="finance",
            doc_ids=["doc_finance"],
            mode="enforce"
        )
        assert allowed is True
        assert violations == []
    
    def test_engineer_access_tech_doc(self, guardrails):
        """測試 engineer 可以存取 tech 文件"""
        allowed, violations = guardrails.enforce_acl(
            user_role="engineer",
            doc_ids=["doc_tech"],
            mode="enforce"
        )
        assert allowed is True
        assert violations == []
    
    def test_engineer_denied_hr(self, guardrails):
        """測試 engineer 被拒絕存取 hr 文件"""
        allowed, violations = guardrails.enforce_acl(
            user_role="engineer",
            doc_ids=["doc_hr"],
            mode="enforce"
        )
        assert allowed is False
        assert "acl_denied:doc_hr" in violations
    
    def test_mode_report_detect_not_block(self, guardrails):
        """測試 report 模式：偵測違規但不阻擋"""
        allowed, violations = guardrails.enforce_acl(
            user_role="employee",
            doc_ids=["doc_finance"],
            mode="report"
        )
        assert allowed is True  # report 模式不阻擋
        assert len(violations) > 0  # 但會記錄違規
    
    def test_multiple_docs_partial_denied(self, guardrails):
        """測試多個文件，部分被拒絕"""
        allowed, violations = guardrails.enforce_acl(
            user_role="employee",
            doc_ids=["doc_public", "doc_finance"],
            mode="enforce"
        )
        assert allowed is False  # 因為有一個被拒絕
        assert "acl_denied:doc_finance" in violations
    
    def test_empty_doc_list(self, guardrails):
        """測試空文件列表"""
        allowed, violations = guardrails.enforce_acl(
            user_role="employee",
            doc_ids=[],
            mode="enforce"
        )
        assert allowed is True
        assert violations == []
    
    def test_unknown_document(self, guardrails):
        """測試未定義的文件（預設拒絕）"""
        allowed, violations = guardrails.enforce_acl(
            user_role="admin",
            doc_ids=["doc_unknown"],
            mode="enforce"
        )
        # 未定義的文件應該被拒絕（因為 roles 會是空列表）
        assert allowed is False
        assert "acl_denied:doc_unknown" in violations