import pytest

from backtester.gate import check_criteria, evaluate

T0 = 1609459200000  # 2021-01-01T00:00:00Z
STEP = 14400000  # 4h en ms

# open/close de docs/gate_p3_calcul_main.md ; high/low choisis coherents (le moteur ne les lit pas)
OHLC = [(100, 101, 99, 100.5), (101, 102.5, 100.5, 102), (102, 105.5, 101.5, 105), (105, 107.5, 104.5, 107)]
CANDLES = [(T0 + i * STEP, float(o), float(h), float(l), float(c)) for i, (o, h, l, c) in enumerate(OHLC)]

# Valeurs qui passent les 4 criteres ; chaque test en change une seule
OK = {"n_trades": 30, "final_normal": 1100.0, "final_doubled": 1050.0, "final_bh": 1080.0}


def criteria(**overrides):
    return check_criteria(**{**OK, **overrides})


def test_bougies_coherentes():
    for _, o, h, l, c in CANDLES:
        assert h >= max(o, c)
        assert l <= min(o, c)


def test_c1_limite():
    assert criteria(n_trades=29)["c1"] is False
    assert criteria(n_trades=30)["c1"] is True


def test_c2_limite_stricte():
    assert criteria(final_normal=1000.0, final_bh=900.0)["c2"] is False
    assert criteria(final_normal=1000.01, final_bh=900.0)["c2"] is True


def test_c3_limite_non_stricte():
    assert criteria(final_doubled=1000.0)["c3"] is True
    assert criteria(final_doubled=999.99)["c3"] is False


def test_c4_egalite_echoue():
    assert criteria(final_normal=1100.0, final_bh=1100.0)["c4"] is False
    assert criteria(final_normal=1100.0, final_bh=1099.99)["c4"] is True


def test_passed_seulement_si_4_vrais():
    assert criteria() == {"c1": True, "c2": True, "c3": True, "c4": True, "passed": True}
    assert criteria(n_trades=29)["passed"] is False
    assert criteria(final_normal=1000.0, final_bh=900.0)["passed"] is False
    assert criteria(final_doubled=999.99)["passed"] is False
    assert criteria(final_bh=1100.0)["passed"] is False


def test_evaluate_buy_and_hold_calcul_main():
    result = evaluate(CANDLES, [1, 1, 1, 1])
    assert result["final_bh"] == pytest.approx(1056.231428310597, abs=1e-6)
    # Cibles toutes a 1 : la strategie est le buy and hold, donc c4 (strict) echoue
    assert result["final_normal"] == pytest.approx(1056.231428310597, abs=1e-6)
    assert result["n_trades"] == 1
    assert result["c4"] is False
    assert result["passed"] is False


def test_evaluate_couts_doubles_pas_meilleurs():
    result = evaluate(CANDLES, [1, 0, 1, 0])
    assert result["n_trades"] == 2
    assert result["final_doubled"] <= result["final_normal"]
    assert set(result) == {"n_trades", "final_normal", "final_doubled", "final_bh", "c1", "c2", "c3", "c4", "passed"}
