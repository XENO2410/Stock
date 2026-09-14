from app.core import risk


def test_position_size_basic():
    r = risk.calc_position_size(capital=50000, risk_per_trade=250, entry_price=100, stop_loss=98)
    assert r["risk_per_share"] == 2.0
    assert r["max_quantity_by_risk"] == 125
    assert r["suggested_quantity"] <= r["max_quantity_by_risk"]


def test_position_size_capital_limited():
    r = risk.calc_position_size(capital=1000, risk_per_trade=500, entry_price=100, stop_loss=99)
    assert r["suggested_quantity"] == 10  # 1000/100
    assert any("Capital limits" in w for w in r["warnings"])


def test_position_size_equal_entry_stop_returns_zero():
    r = risk.calc_position_size(capital=1000, risk_per_trade=100, entry_price=100, stop_loss=100)
    assert r["suggested_quantity"] == 0
    assert r["warnings"]
