from app.core.mock_market import MockMarket
from app.core import signal_engine as se


def test_signal_engine_produces_result_for_seeded_universe():
    m = MockMarket.instance()
    symbol = m.universe()[0]["symbol"]
    res = se.evaluate(symbol, min_confidence=0)
    assert res is not None
    assert res.symbol == symbol
    assert 0 <= res.confidence <= 100
    assert res.action in {"STRONG_BUY", "BUY", "NO_TRADE", "SELL", "STRONG_SELL"}


def test_no_trade_when_threshold_high():
    m = MockMarket.instance()
    symbol = m.universe()[0]["symbol"]
    res = se.evaluate(symbol, min_confidence=101)
    assert res is not None
    assert res.action == "NO_TRADE"
    assert res.direction == "NONE"
