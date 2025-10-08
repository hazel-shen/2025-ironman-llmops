from app.retriever import SimpleRetriever
from pathlib import Path
import jieba

def test_search_top1(tmp_path: Path):
    kb = tmp_path / "kb.jsonl"
    kb.write_text(
        '{"id":"a","text":"hello world vpn sso"}\n'
        '{"id":"b","text":"unrelated text"}\n',
        encoding="utf-8"
    )
    r = SimpleRetriever(str(kb))
    chunks, signals = r.search("vpn 登入", top_k=1)
    assert len(chunks) == 1
    assert chunks[0].id == "a"
    assert signals.max_score >= 0

def test_search_chinese_with_userdict(tmp_path: Path):
    # 建立 KB
    kb = tmp_path / "kb.jsonl"
    kb.write_text(
        '{"id":"faq-001","text":"公司 VPN 設定：下載新版客戶端，並以 SSO 登入。"}\n'
        '{"id":"faq-002","text":"請假流程：登入 HR 系統提交假單。"}\n',
        encoding="utf-8"
    )

    # 建立 userdict
    userdict = tmp_path / "userdict.txt"
    userdict.write_text("請假流程\n公司VPN\n", encoding="utf-8")

    # 載入 userdict
    jieba.initialize()
    jieba.load_userdict(str(userdict))

    r = SimpleRetriever(str(kb))
    chunks, signals = r.search("我要請假流程", top_k=1)

    # 確認檢索命中「請假流程」
    assert len(chunks) == 1
    assert chunks[0].id == "faq-002"
    assert signals.max_score > 0
