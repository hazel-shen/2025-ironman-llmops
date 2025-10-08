# tests/conftest.py
import os
import sys

# 將專案根目錄加入 sys.path（tests 的上一層）
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
