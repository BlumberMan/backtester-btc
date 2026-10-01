"""Tests de la reference naive donchian sur les 11 bougies de docs/donchian_calcul_main.md."""

from donchian_reference import reference_targets

N = 3
M = 2

HIGHS = [10, 11, 12, 12, 14, 15, 14, 12, 11, 17, 16]
LOWS = [8, 9, 10, 10, 11, 12, 11, 9, 9, 10, 8.5]
CLOSES = [9, 10, 11, 12, 13.5, 14, 11.5, 9.5, 10.5, 16, 9]


def test_longueur_et_valeurs():
    cibles = reference_targets(HIGHS, LOWS, CLOSES, N, M)
    assert len(cibles) == 11
    for c in cibles:
        assert c in (0, 1)


def test_warmup():
    cibles = reference_targets(HIGHS, LOWS, CLOSES, N, M)
    assert cibles[0] == 0
    assert cibles[1] == 0
    assert cibles[2] == 0


def test_index_3_close_egal_record():
    # seule valeur calculee a la main : close 12 = record 12, pas d'entree
    cibles = reference_targets(HIGHS, LOWS, CLOSES, N, M)
    assert cibles[3] == 0


def test_causalite():
    cibles = reference_targets(HIGHS, LOWS, CLOSES, N, M)
    for i in range(len(CLOSES)):
        # on multiplie par 10 toutes les bougies apres i
        highs = HIGHS[: i + 1] + [h * 10 for h in HIGHS[i + 1 :]]
        lows = LOWS[: i + 1] + [x * 10 for x in LOWS[i + 1 :]]
        closes = CLOSES[: i + 1] + [c * 10 for c in CLOSES[i + 1 :]]
        modifiees = reference_targets(highs, lows, closes, N, M)
        assert modifiees[: i + 1] == cibles[: i + 1]
