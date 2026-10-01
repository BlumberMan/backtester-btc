"""Tests de la strategie donchian : comparaison avec la reference naive tests/donchian_reference.py
(ecrite separement), anti-lookahead et interface du runner."""

import random
from pathlib import Path

from backtester.runner import check_causality, load_strategy
from donchian_reference import reference_targets

# Chargee comme le runner la charge : prouve qu'elle passe la liste blanche d'imports.
STRATEGY_PATH = Path(__file__).resolve().parent.parent / "backtester" / "strategies" / "donchian.py"
donchian = load_strategy(STRATEGY_PATH)

# Les 11 bougies de docs/donchian_calcul_main.md (n = 3, m = 2).
HIGHS = [10, 11, 12, 12, 14, 15, 14, 12, 11, 17, 16]
LOWS = [8, 9, 10, 10, 11, 12, 11, 9, 9, 10, 8.5]
CLOSES = [9, 10, 11, 12, 13.5, 14, 11.5, 9.5, 10.5, 16, 9]


def to_candles(highs, lows, closes):
    # open n'est pas lu par la strategie : on met le close precedent, comme une vraie serie.
    opens = [closes[0]] + closes[:-1]
    return [(k * 14_400_000, opens[k], highs[k], lows[k], closes[k]) for k in range(len(closes))]


def columns(candles):
    return [c[2] for c in candles], [c[3] for c in candles], [c[4] for c in candles]


def random_candles(rng, count, round_prices):
    """Marche aleatoire avec high >= max(open, close) et low <= min(open, close).

    round_prices arrondit a l'entier : cree des egalites close = record ou close = plancher, le
    cas ou une erreur > / >= se verrait. L'arrondi est croissant, l'ordre high/open/close/low tient.
    """
    candles = []
    price = 1000.0
    for k in range(count):
        open_ = price
        close = open_ + rng.uniform(-4, 4)
        high = max(open_, close) + rng.uniform(0, 3)
        low = min(open_, close) - rng.uniform(0, 3)
        if round_prices:
            open_, high, low, close = (float(round(x)) for x in (open_, high, low, close))
        candles.append((k * 14_400_000, open_, high, low, close))
        price = close
    return candles


def test_warmup():
    assert donchian.WARMUP == max(donchian.N, donchian.M)
    assert type(donchian.WARMUP) is int


def test_onze_bougies_egal_reference():
    candles = to_candles(HIGHS, LOWS, CLOSES)
    targets = donchian.donchian_targets(candles, 3, 2)
    assert targets == reference_targets(HIGHS, LOWS, CLOSES, 3, 2)
    # Seule valeur calculee a la main : close 12 = record 12, pas d'entree.
    assert targets[3] == 0


def test_series_aleatoires_egal_reference():
    rng = random.Random(12345)
    ones = 0
    for s in range(200):
        candles = random_candles(rng, 300, round_prices=(s % 2 == 0))
        highs, lows, closes = columns(candles)
        for n in (2, 3, 5, 10):
            for m in (1, 2, 4, 8):
                targets = donchian.donchian_targets(candles, n, m)
                assert targets == reference_targets(highs, lows, closes, n, m), (s, n, m)
                ones += sum(targets)
    # Garde-fou : la comparaison n'est pas faite que sur des cibles a 0.
    assert ones > 0


def test_anti_lookahead():
    candles = random_candles(random.Random(777), 500, round_prices=False)
    for n, m in ((donchian.N, donchian.M), (3, 2)):
        full = donchian.donchian_targets(candles, n, m)
        for i in range(len(candles)):
            # Toutes les bougies apres i ont high, low et close multiplies par 10.
            changed = candles[:i + 1] + [(t, o, h * 10, l * 10, c * 10) for t, o, h, l, c in candles[i + 1:]]
            assert donchian.donchian_targets(changed, n, m)[:i + 1] == full[:i + 1], (n, m, i)


def test_check_causality():
    candles = random_candles(random.Random(2024), 2000, round_prices=False)
    check_causality(donchian, candles)


def test_compute_targets_interface():
    candles = random_candles(random.Random(99), 1000, round_prices=True)
    targets = donchian.compute_targets(candles)
    assert isinstance(targets, list)
    assert len(targets) == len(candles)
    for t in targets:
        assert type(t) is int
        assert t in (0, 1)
