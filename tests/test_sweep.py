"""Tests du balayage donchian : grille, voisines, regle de choix, et sweep sur bougies synthetiques.
Aucun test ne lit data/ ni le test."""

import ast
import random
from pathlib import Path

import pytest

from backtester import gate
from backtester import sweep as sweep_module
from backtester.runner import load_strategy, period_targets
from backtester.sweep import (
    GRID, GRID_M, GRID_N, STRATEGIES, ChoiceRuleError, choose, main, make_strategy, neighbors, product_grid, sweep,
)

BACKTESTER_DIR = Path(__file__).resolve().parent.parent / "backtester"
SWEEP_PY = BACKTESTER_DIR / "sweep.py"
# Chargee comme le runner la charge, pour fournir la vraie donchian_targets a sweep.
donchian = load_strategy(BACKTESTER_DIR / "strategies" / "donchian.py")


def random_candles(rng, count):
    """Marche aleatoire avec high >= max(open, close) et low <= min(open, close).

    Amplitude assez large pour casser des records de 240 bougies de temps en temps : sinon
    toutes les combinaisons feraient 0 trade et le test de sweep ne verifierait que des zeros.
    """
    candles = []
    price = 1000.0
    for k in range(count):
        open_ = price
        close = open_ + rng.uniform(-10, 10)
        high = max(open_, close) + rng.uniform(0, 3)
        low = min(open_, close) - rng.uniform(0, 3)
        candles.append((k * 14_400_000, open_, high, low, close))
        price = close
    return candles


def grid_results(passing, finals=None):
    """Grille 3x3 construite a la main : passed vrai pour les combinaisons de passing.

    finals donne final_normal par combinaison (1000.0 par defaut). Seules les cles lues par choose
    sont remplies : n, m, passed, final_normal.
    """
    finals = finals or {}
    return [
        {"n": n, "m": m, "passed": (n, m) in passing, "final_normal": finals.get((n, m), 1000.0)}
        for n, m in GRID
    ]


# grille

def test_grille_9_combinaisons_de_donchian_md():
    assert GRID == [
        (60, 30), (60, 60), (60, 120),
        (120, 30), (120, 60), (120, 120),
        (240, 30), (240, 60), (240, 120),
    ]


# voisines

def test_voisines_coin():
    assert neighbors(GRID_N, GRID_M, 60, 30) == [(60, 60), (120, 30)]


def test_voisines_arete():
    assert neighbors(GRID_N, GRID_M, 60, 60) == [(60, 30), (60, 120), (120, 60)]


def test_voisines_centre():
    assert neighbors(GRID_N, GRID_M, 120, 60) == [(60, 60), (120, 30), (120, 120), (240, 60)]


# regle de choix

def test_choose_aucune_ne_passe():
    assert choose(grid_results(set())) is None


def test_choose_une_seule_passe_isolee():
    assert choose(grid_results({(120, 60)})) is None


def test_choose_bloc_coin_avec_ses_voisines():
    # (60, 30) et ses 2 voisines passent. Les voisines ont un meilleur capital mais ne sont pas
    # candidates : (60, 60) a (60, 120) et (120, 60) qui echouent, (120, 30) a (120, 60) et (240, 30).
    passing = {(60, 30), (60, 60), (120, 30)}
    finals = {(60, 30): 1100.0, (60, 60): 1500.0, (120, 30): 1400.0}
    chosen = choose(grid_results(passing, finals))
    assert (chosen["n"], chosen["m"]) == (60, 30)


def test_choose_plusieurs_candidates_meilleur_final_normal():
    # Tout passe sauf (240, 120). Candidates : toutes sauf (240, 120) et ses voisines (120, 120)
    # et (240, 60). (240, 60) a le plus gros capital mais n'est pas candidate.
    passing = set(GRID) - {(240, 120)}
    finals = {(60, 30): 1100.0, (60, 60): 1200.0, (120, 30): 1300.0, (240, 60): 9999.0}
    chosen = choose(grid_results(passing, finals))
    assert (chosen["n"], chosen["m"]) == (120, 30)


def test_choose_egalite_exacte_refusee():
    finals = {(60, 30): 1300.0, (120, 30): 1300.0}
    with pytest.raises(ChoiceRuleError, match="egalite exacte"):
        choose(grid_results(set(GRID), finals))


def test_choose_grille_incomplete_refusee():
    with pytest.raises(ChoiceRuleError):
        choose(grid_results(set(GRID))[:8])


# sweep

def test_sweep_9_resultats_ordre_de_la_grille():
    candles = random_candles(random.Random(42), 800)
    results = sweep(candles, GRID, donchian.donchian_targets)
    assert [(r["n"], r["m"]) for r in results] == GRID
    for r in results:
        assert set(r) == {"n", "m", "n_trades", "final_normal", "final_doubled", "final_bh",
                          "c1", "c2", "c3", "c4", "passed"}
    # Garde-fou : les bougies synthetiques font trader au moins une combinaison.
    assert sum(r["n_trades"] for r in results) > 0


def test_wrapper_120_60_egal_compute_targets_du_module():
    candles = random_candles(random.Random(7), 800)
    wrapper = make_strategy(donchian.donchian_targets, 120, 60)
    assert wrapper.WARMUP == donchian.WARMUP
    assert wrapper.compute_targets(candles) == donchian.compute_targets(candles)
    # Et sweep juge (120, 60) exactement comme run_train jugerait le module donchian.
    result = sweep(candles, [(120, 60)], donchian.donchian_targets)[0]
    assert result == {"n": 120, "m": 60, **gate.evaluate(candles, period_targets(donchian, [], candles))}


def test_sweep_warmup_superieur_aux_bougies_refuse():
    candles = random_candles(random.Random(1), 200)
    with pytest.raises(ValueError, match="WARMUP"):
        sweep(candles, [(240, 30)], donchian.donchian_targets)


# gardes

def test_sweep_n_importe_pas_holdout():
    tree = ast.parse(SWEEP_PY.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all("holdout" not in a.name for a in node.names)
        if isinstance(node, ast.ImportFrom):
            assert "holdout" not in (node.module or "")
            assert all("holdout" not in a.name for a in node.names)


# sma-cross : grille, voisines, regle de choix et sweep avec les noms ("f", "s")

SMA_F, SMA_S = STRATEGIES["sma-cross"]["grids"]
SMA_GRID = product_grid(SMA_F, SMA_S)
SMA_NAMES = STRATEGIES["sma-cross"]["names"]


def sma_grid_results(passing, finals=None):
    """Comme grid_results, sur la grille sma-cross et avec les cles f, s."""
    finals = finals or {}
    return [
        {"f": f, "s": s, "passed": (f, s) in passing, "final_normal": finals.get((f, s), 1000.0)}
        for f, s in SMA_GRID
    ]


def test_sma_cross_grille_9_combinaisons_de_sma_cross_md():
    # Liste numerotee 1 a 9 de docs/strategies/sma-cross.md, dans l'ordre.
    assert SMA_GRID == [
        (30, 120), (30, 180), (30, 240),
        (60, 120), (60, 180), (60, 240),
        (90, 120), (90, 180), (90, 240),
    ]
    assert SMA_NAMES == ("f", "s")
    assert STRATEGIES["sma-cross"]["targets"] == "sma_cross_targets"


def test_sma_cross_s_toujours_superieur_a_f():
    # Condition pour que WARMUP = max(F, S) de make_strategy soit bien le WARMUP = S de sma-cross.md.
    assert all(s > f for f, s in SMA_GRID)
    assert all(make_strategy(None, f, s).WARMUP == s for f, s in SMA_GRID)


def test_sma_cross_voisines_coin():
    assert neighbors(SMA_F, SMA_S, 30, 120) == [(30, 180), (60, 120)]


def test_sma_cross_voisines_centre():
    assert neighbors(SMA_F, SMA_S, 60, 180) == [(30, 180), (60, 120), (60, 240), (90, 180)]


def test_sma_cross_choose_aucune_ne_passe():
    assert choose(sma_grid_results(set()), SMA_F, SMA_S, SMA_NAMES) is None


def test_sma_cross_choose_une_seule_passe_isolee():
    assert choose(sma_grid_results({(60, 180)}), SMA_F, SMA_S, SMA_NAMES) is None


def test_sma_cross_choose_bloc_coin_avec_ses_voisines():
    # Meme structure que le test donchian : seules (30, 120) et ses 2 voisines passent, et les
    # voisines, mieux payees, ne sont pas candidates car leurs propres voisines echouent.
    passing = {(30, 120), (30, 180), (60, 120)}
    finals = {(30, 120): 1100.0, (30, 180): 1500.0, (60, 120): 1400.0}
    chosen = choose(sma_grid_results(passing, finals), SMA_F, SMA_S, SMA_NAMES)
    assert (chosen["f"], chosen["s"]) == (30, 120)


def test_sma_cross_choose_egalite_message_avec_f_et_s():
    finals = {(30, 120): 1300.0, (60, 120): 1300.0}
    with pytest.raises(ChoiceRuleError, match="F=30 S=120, F=60 S=120"):
        choose(sma_grid_results(set(SMA_GRID), finals), SMA_F, SMA_S, SMA_NAMES)


def test_resultats_sma_cross_refuses_par_la_grille_donchian_par_defaut():
    # Des resultats d'une grille ne doivent pas etre juges avec la regle d'une autre.
    with pytest.raises(ChoiceRuleError):
        choose(sma_grid_results(set()), names=SMA_NAMES)


def test_sma_cross_sweep_9_resultats_cles_f_s():
    candles = random_candles(random.Random(3), 300)
    results = sweep(candles, SMA_GRID, lambda c, f, s: [0] * len(c), SMA_NAMES)
    assert [(r["f"], r["s"]) for r in results] == SMA_GRID
    for r in results:
        assert set(r) == {"f", "s", "n_trades", "final_normal", "final_doubled", "final_bh",
                          "c1", "c2", "c3", "c4", "passed"}
        assert r["n_trades"] == 0


# ligne de commande

def _interdire_data(monkeypatch):
    # Si argparse laissait passer, la premiere lecture de data/ ferait echouer le test.
    def interdit(*args, **kwargs):
        raise AssertionError("data/ lu alors que l'argument devait etre refuse")
    monkeypatch.setattr(sweep_module, "check_data_hash", interdit)
    monkeypatch.setattr(sweep_module, "load_train", interdit)


def test_main_sans_nom_refuse(monkeypatch):
    _interdire_data(monkeypatch)
    with pytest.raises(SystemExit):
        main([])


def test_main_nom_inconnu_refuse(monkeypatch):
    _interdire_data(monkeypatch)
    with pytest.raises(SystemExit):
        main(["inconnu"])
