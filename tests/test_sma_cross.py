"""Tests de la strategie sma-cross : egalite exacte avec la reference naive
tests/sma_cross_reference.py (ecrite separement), cas d'egalite des SMA, warmup et demarrage neutre,
anti-lookahead et interface du runner."""

import random
from pathlib import Path

from backtester.runner import check_causality, load_strategy, period_targets
from sma_cross_reference import reference_targets

# Chargee comme le runner la charge : prouve qu'elle passe la liste blanche d'imports.
STRATEGY_PATH = Path(__file__).resolve().parent.parent / "backtester" / "strategies" / "sma-cross.py"
sma_cross = load_strategy(STRATEGY_PATH)

# Grille de docs/strategies/sma-cross.md.
GRID_F = (30, 60, 90)
GRID_S = (120, 180, 240)


def to_candles(closes):
    # Seul le close est lu par la strategie : open = close precedent, high et low encadrent.
    opens = [closes[0]] + closes[:-1]
    return [(k * 14_400_000, opens[k], max(opens[k], closes[k]) + 1, min(opens[k], closes[k]) - 1, closes[k])
            for k in range(len(closes))]


def random_candles(rng, count, gaps):
    """Marche aleatoire avec high >= max(open, close) et low <= min(open, close).

    gaps : l'open de chaque bougie s'ecarte du close precedent, donc close[t] != open[t+1]. Une
    strategie qui lirait open[t+1] au lieu de close[t] ne verrait pas la meme valeur.
    """
    candles = []
    price = 1000.0
    for k in range(count):
        open_ = price + (rng.choice((-1, 1)) * rng.uniform(0.5, 2) if gaps else 0.0)
        close = open_ + rng.uniform(-4, 4)
        high = max(open_, close) + rng.uniform(0, 3)
        low = min(open_, close) - rng.uniform(0, 3)
        candles.append((k * 14_400_000, open_, high, low, close))
        price = close
    return candles


def closes_of(candles):
    return [c[4] for c in candles]


def test_warmup():
    assert sma_cross.WARMUP == sma_cross.S
    assert type(sma_cross.WARMUP) is int
    assert sma_cross.F in GRID_F and sma_cross.S in GRID_S


# 1. Egalite exacte avec la reference naive

def test_series_aleatoires_egal_reference_grille():
    rng = random.Random(4242)
    ones = 0
    for serie in range(12):
        candles = random_candles(rng, 900, gaps=(serie % 2 == 0))
        closes = closes_of(candles)
        for f in GRID_F:
            for s in GRID_S:
                targets = sma_cross.sma_cross_targets(candles, f, s)
                # == sur des listes d'int : aucune tolerance, chaque cible doit etre la meme.
                assert targets == reference_targets(closes, f, s), (serie, f, s)
                ones += sum(targets)
    # Garde-fou : la comparaison n'est pas faite que sur des cibles a 0.
    assert ones > 0


def test_sma_identique_bit_a_bit():
    # Les cibles dependent de comparaisons entre SMA : on verifie aussi les valeurs elles-memes,
    # recalculees a la main comme la reference (somme de gauche a droite partant de 0).
    closes = closes_of(random_candles(random.Random(31), 400, gaps=True))
    for n in GRID_F + GRID_S:
        for i in range(n - 1, len(closes)):
            total = 0
            for j in range(i - n + 1, i + 1):
                total = total + closes[j]
            assert sma_cross.sma(closes, n, i) == total / n, (n, i)


def test_petits_parametres_egal_reference():
    # Petites fenetres : beaucoup plus de croisements, donc beaucoup plus de decisions comparees.
    rng = random.Random(777)
    for serie in range(50):
        candles = random_candles(rng, 300, gaps=(serie % 2 == 1))
        closes = closes_of(candles)
        for f, s in ((1, 2), (2, 5), (3, 10), (5, 20)):
            assert sma_cross.sma_cross_targets(candles, f, s) == reference_targets(closes, f, s), (serie, f, s)


# 2. Cas d'egalite SMA_F == SMA_S, construits a la main
# Avec F = 1 et S = 2 : SMA_F[i] = close[i] et SMA_S[i] = (close[i-1] + close[i]) / 2, donc
# SMA_F > SMA_S si close[i] > close[i-1], et SMA_F == SMA_S si close[i] == close[i-1].

def test_entree_egalite_en_i_moins_1():
    # i=2 : en 1, F=10 et S=10 (egales) ; en 2, F=12 > S=11 -> entree. Avec < au lieu de <= : rien.
    assert sma_cross.sma_cross_targets(to_candles([10, 10, 12]), 1, 2) == [0, 0, 1]


def test_pas_d_entree_egalite_en_i():
    # i=2 : en 1, F=9 < S=9.5 ; en 2, F=9 == S=9 -> pas d'entree (strict). Avec >= : entree en 2.
    # i=3 : en 2, egales ; en 3, F=10 > S=9.5 -> entree.
    assert sma_cross.sma_cross_targets(to_candles([10, 9, 9, 10]), 1, 2) == [0, 0, 0, 1]


def test_sortie_egalites():
    # i=2 : entree (10 == 10 puis 12 > 11).
    # i=3 : F=12 == S=12 -> pas de sortie (strict). Avec <= : sortie en 3.
    # i=4 : en 3, egales ; en 4, F=11 < S=11.5 -> sortie. Avec > au lieu de >= : on resterait long.
    assert sma_cross.sma_cross_targets(to_candles([10, 10, 12, 12, 11]), 1, 2) == [0, 0, 1, 1, 0]


def test_egalites_egal_reference():
    for closes in ([10, 10, 12], [10, 9, 9, 10], [10, 10, 12, 12, 11]):
        assert sma_cross.sma_cross_targets(to_candles(closes), 1, 2) == reference_targets(closes, 1, 2)


# 3. Cibles a 0 pendant le warmup et etat neutre au debut de la periode

def test_cibles_a_0_pendant_le_warmup():
    candles = random_candles(random.Random(5), 600, gaps=True)
    for f in GRID_F:
        for s in GRID_S:
            assert sma_cross.sma_cross_targets(candles, f, s)[:s] == [0] * s, (f, s)


def test_demarrage_neutre_petits_parametres():
    # Fin du warmup (i=2) : F=15 > S=14.5, la rapide est deja au-dessus. Pas de croisement ensuite
    # (clotures croissantes) : on reste neutre jusqu'au bout.
    assert sma_cross.sma_cross_targets(to_candles([10, 14, 15, 16, 17]), 1, 2) == [0, 0, 0, 0, 0]


def test_demarrage_neutre_compute_targets():
    # Clotures strictement croissantes : des la fin du warmup la rapide est au-dessus de la lente
    # et ne la recroise jamais. Une strategie qui supposerait une position deja ouverte, ou qui
    # entrerait parce que "rapide > lente" sans croisement, aurait des cibles a 1.
    closes = [1000.0 + k for k in range(sma_cross.WARMUP + 300)]
    assert sma_cross.compute_targets(to_candles(closes)) == [0] * len(closes)


def test_demarrage_neutre_period_targets_avec_historique():
    # Comme au test : l'historique (WARMUP bougies) monte, la periode continue de monter. L'etat
    # repart neutre au debut de compute_targets(history + period), aucune cible a 1.
    closes = [1000.0 + k for k in range(sma_cross.WARMUP + 200)]
    candles = to_candles(closes)
    history, period = candles[:sma_cross.WARMUP], candles[sma_cross.WARMUP:]
    assert period_targets(sma_cross, history, period) == [0] * len(period)
    # Sans historique (train) : les WARMUP premieres cibles sont forcees a 0, le reste aussi.
    assert period_targets(sma_cross, [], candles) == [0] * len(candles)


# 4. Anti-lookahead, ecrit a la main

def test_anti_lookahead():
    candles = random_candles(random.Random(2026), 420, gaps=True)
    # Les donnees separent bien close[t] et open[t+1].
    assert all(candles[t][4] != candles[t + 1][1] for t in range(len(candles) - 1))
    for f, s in ((sma_cross.F, sma_cross.S), (30, 120), (2, 5)):
        full = sma_cross.sma_cross_targets(candles, f, s)
        assert sum(full) > 0, (f, s)  # sinon le test ne verifierait que des 0
        for t in range(len(candles)):
            # Toutes les bougies apres t ont open, high, low et close multiplies par 10.
            changed = candles[:t + 1] + [(ts, o * 10, h * 10, l * 10, c * 10) for ts, o, h, l, c in candles[t + 1:]]
            assert sma_cross.sma_cross_targets(changed, f, s)[:t + 1] == full[:t + 1], (f, s, t)


# 5. check_causality et interface

def test_check_causality():
    candles = random_candles(random.Random(2024), 2000, gaps=True)
    check_causality(sma_cross, candles)


def test_compute_targets_interface():
    candles = random_candles(random.Random(99), 1000, gaps=True)
    targets = sma_cross.compute_targets(candles)
    assert targets == sma_cross.sma_cross_targets(candles, sma_cross.F, sma_cross.S)
    assert isinstance(targets, list)
    assert len(targets) == len(candles)
    for t in targets:
        assert type(t) is int
        assert t in (0, 1)
