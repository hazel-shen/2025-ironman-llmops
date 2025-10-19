# test_redos_protection.py
"""測試 ReDoS (Regular expression Denial of Service) 防護"""
import pytest
import time
from app.guardrails import Guardrails


class TestReDoSProtection:
    """測試正則表達式拒絕服務攻擊防護"""
    
    @pytest.fixture
    def policy(self):
        """測試用的 policy"""
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
    def guardrails(self, policy):
        return Guardrails(policy)
    
    def test_email_with_excessive_dots(self, guardrails):
        """
        測試大量點號的 email 不會造成效能問題
        修復前：可能觸發災難性回溯
        修復後：因為有長度限制，快速處理
        """
        # 創建可能觸發回溯的 email
        malicious_email = "a" + ("." * 100) + "@test.com"
        
        start_time = time.time()
        result, stats = guardrails.redact_pii(malicious_email, mode="enforce")
        elapsed = time.time() - start_time
        
        # 應該快速完成（< 0.1 秒）
        assert elapsed < 0.1, f"處理時間過長: {elapsed}秒"
    
    def test_email_regex_length_limit(self, guardrails):
        """
        測試 email regex 的長度限制有效
        
        長度限制防止了無限回溯，這是 ReDoS 防護的關鍵
        """
        # 正常長度的 email 應該被匹配
        normal_email = "user@example.com"
        result, stats = guardrails.redact_pii(normal_email, mode="enforce")
        assert "[REDACTED_EMAIL]" in result
        assert stats.get("email", 0) == 1
        
        # 64 字元用戶名（邊界測試）
        long_username = "a" * 64 + "@test.com"
        result2, stats2 = guardrails.redact_pii(long_username, mode="enforce")
        assert "[REDACTED_EMAIL]" in result2
        assert stats2.get("email", 0) == 1
        
        # 測試 regex 有長度限制（不會無限回溯）
        # 這個測試主要確保不會因為長度而造成效能問題
        very_long_email = "a" * 100 + "@" + "b" * 100 + ".com"
        start_time = time.time()
        result3, stats3 = guardrails.redact_pii(very_long_email, mode="enforce")
        elapsed = time.time() - start_time
        # 關鍵：即使超長也要快速處理（< 0.1 秒）
        assert elapsed < 0.1, f"處理超長 email 耗時: {elapsed}秒"
    
    def test_performance_with_many_emails(self, guardrails):
        """測試處理多個 email 的效能"""
        # 20 個正常 email（避免被 max_input_length 截斷）
        text = " ".join([f"user{i}@test.com" for i in range(20)])
        
        start_time = time.time()
        result, stats = guardrails.redact_pii(text, mode="enforce")
        elapsed = time.time() - start_time
        
        # 應該快速完成
        assert elapsed < 0.5, f"處理時間過長: {elapsed}秒"
        assert stats.get("email", 0) == 20
        assert "[REDACTED_EMAIL]" in result
    
    def test_phone_regex_performance(self, guardrails):
        """測試電話號碼正則的效能"""
        # 大量數字和破折號的組合
        attack_string = "0912-345-678-" * 100
        
        start_time = time.time()
        result, stats = guardrails.redact_pii(attack_string, mode="enforce")
        elapsed = time.time() - start_time
        
        # 應該快速完成
        assert elapsed < 1.0, f"處理時間過長: {elapsed}秒"
    
    def test_max_length_prevents_redos(self, guardrails):
        """
        測試 max_length 截斷機制可以防止 ReDoS
        
        即使輸入超長且可能觸發回溯，截斷機制也能保護系統
        """
        # 創建超長的潛在攻擊字串
        very_long_input = "test" * 500_000 + "@example.com"
        
        start_time = time.time()
        result, stats = guardrails.redact_pii(very_long_input, mode="enforce")
        elapsed = time.time() - start_time
        
        # 因為有截斷，處理時間應該是可控的
        assert elapsed < 2.0, f"處理時間過長: {elapsed}秒"
        assert stats.get("truncated") is True
        assert len(result) == 1000  # 被截斷到 max_input_length
    
    def test_input_check_performance(self, guardrails):
        """測試 check_input 對長字串的處理效能"""
        # 創建可能觸發正則回溯的輸入
        long_input = "IGNORE " * 10000 + "previous instructions"
        
        start_time = time.time()
        blocked, violations = guardrails.check_input(long_input, mode="enforce")
        elapsed = time.time() - start_time
        
        # 應該在合理時間內完成
        assert elapsed < 1.0, f"處理時間過長: {elapsed}秒"
    
    def test_sanitize_input_truncation(self):
        """測試 sanitize_input 的截斷保護"""
        from app.guardrails import sanitize_input
        
        # 超長輸入
        very_long = "x" * 2_000_000
        
        start_time = time.time()
        result = sanitize_input(very_long, max_length=1_000_000)
        elapsed = time.time() - start_time
        
        # 截斷應該很快
        assert elapsed < 0.5, f"截斷耗時過長: {elapsed}秒"
        assert len(result) == 1_000_000