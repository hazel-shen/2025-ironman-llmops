from app.router import decide, THRESH_MAX, THRESH_AVG
from app.models import RetrievalSignals

def test_route_kb():
    sig = RetrievalSignals(
        max_score=THRESH_MAX + 0.05,
        avg_topk=0.0,
        num_docs=2,
        context_len=100
    )
    r = decide(sig)
    assert r.target == "kb"

def test_route_small():
    sig = RetrievalSignals(
        max_score=0.1,
        avg_topk=0.1,
        num_docs=0,
        context_len=0
    )
    r = decide(sig)
    assert r.target == "small_model"

def test_route_avg_too_low():
    """模糊命中：有文件，但平均分數不足，應該走 small_model"""
    sig = RetrievalSignals(
        max_score=THRESH_MAX - 0.01,   # 接近但未達 max 門檻
        avg_topk=THRESH_AVG - 0.01,    # 低於 avg 門檻
        num_docs=2,
        context_len=50
    )
    r = decide(sig)
    assert r.target == "small_model"

def test_route_avg_only_triggers_kb():
    """即使 max_score 未達門檻，只要 avg_topk 過門檻也應走 KB"""
    sig = RetrievalSignals(
        max_score=THRESH_MAX - 0.05,   # 沒達到 max 門檻
        avg_topk=THRESH_AVG + 0.02,    # 平均分數過門檻
        num_docs=3,                    # 至少命中一份文件
        context_len=120
    )
    r = decide(sig)
    assert r.target == "kb"
