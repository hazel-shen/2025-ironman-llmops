import jieba

def test_userdict(tmp_path):
    # 準備一個 userdict
    dict_path = tmp_path / "userdict.txt"
    dict_path.write_text("請假流程\n公司VPN\n", encoding="utf-8")

    jieba.initialize()
    jieba.load_userdict(str(dict_path))

    segs = list(jieba.cut("我要查請假流程", HMM=True))
    assert "請假流程" in segs

    segs = list(jieba.cut("如何設定公司VPN", HMM=True))
    assert "公司VPN" in segs
