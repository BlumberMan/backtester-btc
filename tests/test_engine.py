import pytest

from backtester.engine import run_backtest

T0 = 1609459200000  # 2021-01-01T00:00:00Z
STEP = 14400000  # 4h en ms

OHLC = [
    (100, 102, 99, 101), (101, 103, 100, 102), (102, 106, 101, 105), (105, 109, 104, 108), (108, 110, 106, 107),
    (110, 111, 107, 109), (109, 110, 104, 105), (104, 106, 100, 102), (102, 103, 97, 98), (98, 101, 97, 100),
]
CANDLES = [(T0 + i * STEP, float(o), float(h), float(l), float(c)) for i, (o, h, l, c) in enumerate(OHLC)]
GATE_TARGETS = [0, 1, 1, 1, 0, 0, 1, 1, 1, 1]


def test_gate_p2_calcul_main():
    # Valeurs attendues issues de docs/gate_p2_calcul_main.md : immuables
    result = run_backtest(CANDLES, GATE_TARGETS)
    assert result.final_cash == pytest.approx(1030.74808821717, abs=0.01)
    assert result.final_cash == pytest.approx(1030.74808821717, abs=1e-6)
    assert len(result.trades) == 2

    t1, t2 = result.trades
    assert t1.entry_time == CANDLES[2][0]
    assert t1.entry_price == pytest.approx(102.051, abs=1e-6)
    assert t1.exit_time == CANDLES[5][0]
    assert t1.exit_price == pytest.approx(109.945, abs=1e-6)
    assert t1.pnl == pytest.approx(75.19985051591851, abs=1e-6)

    assert t2.entry_time == CANDLES[7][0]
    assert t2.entry_price == pytest.approx(104.052, abs=1e-6)
    assert t2.exit_time == CANDLES[9][0]
    assert t2.exit_price == pytest.approx(99.95, abs=1e-6)
    assert t2.pnl == pytest.approx(-44.45176229874926, abs=1e-6)


def test_cibles_toutes_a_zero():
    result = run_backtest(CANDLES, [0] * 10)
    assert result.final_cash == 1000.0
    assert result.trades == []


def test_cible_finale_ignoree():
    result = run_backtest(CANDLES, [0] * 9 + [1])
    assert result.final_cash == 1000.0
    assert result.trades == []


def test_anti_lookahead_execution_open_suivant():
    # Bougies dédiées : dans CANDLES, close[0] == open[1] (101), le test ne discriminerait rien
    candles = [(T0, 100.0, 102.0, 99.0, 101.0), (T0 + STEP, 103.0, 104.0, 102.0, 103.5), (T0 + 2 * STEP, 104.0, 105.0, 103.0, 104.5)]
    result = run_backtest(candles, [1, 0, 0], fee=0, slippage=0)
    entry_price = result.trades[0].entry_price
    assert entry_price == candles[1][1]
    assert entry_price != candles[0][4]


def test_buy_and_hold_sans_frais():
    # Cible 1 décidée en t=0 : achat à l'open de la bougie 1, jamais de vente
    result = run_backtest(CANDLES, [1] * 10, fee=0, slippage=0)
    assert result.final_cash == pytest.approx(1000 * CANDLES[-1][4] / CANDLES[1][1], abs=1e-9)


def test_frais_et_slippage_doubles_reduisent_le_capital():
    base = run_backtest(CANDLES, GATE_TARGETS)
    doubled = run_backtest(CANDLES, GATE_TARGETS, fee=0.002, slippage=0.001)
    assert doubled.final_cash < base.final_cash


def test_longueurs_differentes():
    with pytest.raises(ValueError):
        run_backtest(CANDLES, [0] * 9)


def test_cible_invalide():
    with pytest.raises(ValueError):
        run_backtest(CANDLES, [0] * 9 + [2])


def test_liste_vide():
    result = run_backtest([], [])
    assert result.final_cash == 1000.0
    assert result.trades == []
