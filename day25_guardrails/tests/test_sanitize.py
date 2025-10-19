# test_sanitize.py
"""測試 guardrails.py 中的 sanitize_input 和 compile_patterns 函數"""
import pytest
from app.guardrails import sanitize_input, compile_patterns


class TestSanitizeInput:
    """測試輸入清理功能"""
    
    def test_empty_string(self):
        """測試空字串"""
        assert sanitize_input("") == ""
    
    def test_none_input(self):
        """測試 None 輸入"""
        assert sanitize_input(None) == ""
    
    def test_normal_text(self):
        """測試正常文字"""
        result = sanitize_input("Hello World")
        assert "Hello" in result
        assert "World" in result
    
    def test_max_length_truncation(self):
        """測試超長輸入被截斷 (防 ReDoS)"""
        long_text = "a" * 1_500_000
        result = sanitize_input(long_text, max_length=1_000_000)
        assert len(result) == 1_000_000
    
    def test_remove_null_bytes(self):
        """測試移除 null bytes"""
        text = "hello\x00world"
        result = sanitize_input(text)
        assert "\x00" not in result
        assert "hello" in result
        assert "world" in result
    
    def test_remove_control_characters(self):
        """測試移除控制字元"""
        text = "test\x01\x1f\x7fdata"
        result = sanitize_input(text)
        assert "\x01" not in result
        assert "\x1f" not in result
        assert "\x7f" not in result
    
    def test_remove_html_script_tags(self):
        """測試移除 <script> 標籤"""
        text = "<script>alert('xss')</script>hello"
        result = sanitize_input(text)
        assert "<script>" not in result
        assert "</script>" not in result
    
    def test_remove_html_div_tags(self):
        """測試移除 HTML 標籤"""
        text = "<div>content</div>"
        result = sanitize_input(text)
        assert "<div>" not in result
    
    def test_html_escape_special_chars(self):
        """測試 HTML 特殊字元被轉義"""
        text = "<>&\""
        result = sanitize_input(text)
        # HTML escape 應該轉換這些字元
        assert "<" not in result or "&lt;" in result
        assert ">" not in result or "&gt;" in result


class TestCompilePatterns:
    """測試正則表達式編譯功能"""
    
    def test_empty_list(self):
        """測試空列表"""
        patterns = compile_patterns([])
        assert patterns == []
    
    def test_single_pattern(self):
        """測試單一正則"""
        patterns = compile_patterns([r"\d+"])
        assert len(patterns) == 1
        assert patterns[0].search("123") is not None
    
    def test_multiple_patterns(self):
        """測試多個正則"""
        patterns = compile_patterns([r"\d+", r"[a-z]+"])
        assert len(patterns) == 2
        assert patterns[0].search("123") is not None
        assert patterns[1].search("abc") is not None