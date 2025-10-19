# test_guardrails_init.py
"""測試 Guardrails 類別的初始化和配置讀取"""
import pytest
from app.guardrails import Guardrails


class TestGuardrailsInit:
    """測試 Guardrails 初始化"""
    
    def test_init_with_full_policy(self):
        """測試完整 policy 初始化"""
        policy = {
            "input": {
                "deny_patterns": [r"test1", r"test2"]
            },
            "output": {
                "deny_patterns": [r"output1"]
            },
            "io_limit": {
                "max_input_length": 5000,
                "max_output_length": 3000
            },
            "pii": {
                "redact": ["email", "phone"]
            },
            "retrieval": {
                "docs": {
                    "doc1": {"roles": ["admin"]}
                }
            }
        }
        gr = Guardrails(policy)
        
        assert gr.max_input_length == 5000
        assert gr.max_output_length == 3000
        assert len(gr.input_patterns) == 2
        assert len(gr.output_patterns) == 1
    
    def test_init_with_minimal_policy(self):
        """測試最小 policy（使用預設值）"""
        policy = {}
        gr = Guardrails(policy)
        
        # 應該使用預設值
        assert gr.max_input_length == 1_000_000
        assert gr.max_output_length == 500_000
        assert gr.input_patterns == []
        assert gr.output_patterns == []
    
    def test_init_with_partial_io_limit(self):
        """測試部分 io_limit 配置"""
        policy = {
            "io_limit": {
                "max_input_length": 2000
                # max_output_length 使用預設值
            }
        }
        gr = Guardrails(policy)
        
        assert gr.max_input_length == 2000
        assert gr.max_output_length == 500_000  # 預設值
    
    def test_init_input_patterns_only(self):
        """測試只有 input patterns"""
        policy = {
            "input": {
                "deny_patterns": [r"bad\s+word", r"\d{3}-\d{3}"]
            }
        }
        gr = Guardrails(policy)
        
        assert len(gr.input_patterns) == 2
        assert len(gr.output_patterns) == 0
    
    def test_init_output_patterns_only(self):
        """測試只有 output patterns"""
        policy = {
            "output": {
                "deny_patterns": [r"confidential"]
            }
        }
        gr = Guardrails(policy)
        
        assert len(gr.input_patterns) == 0
        assert len(gr.output_patterns) == 1
    
    def test_patterns_are_compiled(self):
        """測試 patterns 確實被編譯成正則表達式"""
        policy = {
            "input": {
                "deny_patterns": [r"\d+"]
            }
        }
        gr = Guardrails(policy)
        
        # 驗證是編譯過的正則表達式物件
        assert hasattr(gr.input_patterns[0], 'search')
        assert gr.input_patterns[0].search("123") is not None
    
    def test_empty_deny_patterns(self):
        """測試空的 deny_patterns"""
        policy = {
            "input": {
                "deny_patterns": []
            },
            "output": {
                "deny_patterns": []
            }
        }
        gr = Guardrails(policy)
        
        assert gr.input_patterns == []
        assert gr.output_patterns == []
    
    def test_policy_without_input_section(self):
        """測試沒有 input section 的 policy"""
        policy = {
            "output": {
                "deny_patterns": [r"test"]
            }
        }
        gr = Guardrails(policy)
        
        assert gr.input_patterns == []
        assert len(gr.output_patterns) == 1
    
    def test_policy_without_output_section(self):
        """測試沒有 output section 的 policy"""
        policy = {
            "input": {
                "deny_patterns": [r"test"]
            }
        }
        gr = Guardrails(policy)
        
        assert len(gr.input_patterns) == 1
        assert gr.output_patterns == []
    
    def test_policy_without_pii_section(self):
        """測試沒有 pii section 的 policy"""
        policy = {
            "input": {
                "deny_patterns": [r"test"]
            }
        }
        gr = Guardrails(policy)
        
        # redact_pii 應該仍然可以運作（只是不會遮罩任何東西）
        result, stats = gr.redact_pii("test@example.com", mode="enforce")
        assert "test@example.com" in result  # 因為沒有 pii config
    
    def test_policy_without_retrieval_section(self):
        """測試沒有 retrieval section 的 policy"""
        policy = {
            "input": {
                "deny_patterns": [r"test"]
            }
        }
        gr = Guardrails(policy)
        
        # enforce_acl 應該仍然可以運作
        allowed, violations = gr.enforce_acl("admin", ["doc1"], mode="enforce")
        # 因為沒有定義文件，所以會被拒絕
        assert allowed is False
    
    def test_custom_max_lengths(self):
        """測試自訂長度限制"""
        policy = {
            "io_limit": {
                "max_input_length": 100,
                "max_output_length": 50
            }
        }
        gr = Guardrails(policy)
        
        assert gr.max_input_length == 100
        assert gr.max_output_length == 50
        
        # 驗證 check_input 使用這個限制
        long_input = "a" * 200
        blocked, violations = gr.check_input(long_input, mode="enforce")
        # 不會因為長度被阻擋，但會被截斷
        assert blocked is False
    
    def test_policy_is_stored(self):
        """測試 policy 被正確儲存"""
        policy = {
            "input": {"deny_patterns": [r"test"]},
            "custom_field": "custom_value"
        }
        gr = Guardrails(policy)
        
        assert gr.policy == policy
        assert gr.policy.get("custom_field") == "custom_value"