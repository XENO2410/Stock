import numpy as np

from app.core import indicators as ind


def test_ema_matches_manual():
    v = [1, 2, 3, 4, 5]
    out = ind.ema(v, 3)
    assert abs(out[-1] - 4.0625) < 0.5


def test_sma_returns_correct_length():
    v = list(range(20))
    out = ind.sma(v, 5)
    assert out.shape[0] == 20
    assert not np.isnan(out[-1])


def test_rsi_bounds():
    v = np.linspace(100, 200, 100).tolist()
    r = ind.rsi(v, 14)
    assert 0.0 <= float(r[-1]) <= 100.0


def test_vwap_zero_volume_returns_last_price():
    val = ind.vwap([1, 2], [1, 2], [1, 2], [0, 0])
    assert val == 2


def test_classic_pivots_symmetric():
    p = ind.classic_pivots(prev_high=110, prev_low=90, prev_close=100)
    assert abs(p.pivot - 100) < 1e-6
    assert p.r1 > p.pivot > p.s1
