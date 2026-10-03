"""Tests de la reference naive sma-cross sur deux petites series calculees a la main."""

from sma_cross_reference import reference_targets

F = 1
S = 2

CLOSES_A = [10, 10, 12, 14, 11, 9, 9, 13]
CLOSES_B = [10, 14, 15, 16, 17]


def test_cas_a():
    # valeurs calculees a la main : entree en 2, sortie en 4, entree en 7
    assert reference_targets(CLOSES_A, F, S) == [0, 0, 1, 1, 0, 0, 0, 1]


def test_cas_b():
    # la rapide est deja au-dessus de la lente a la fin du warmup : pas de croisement, on reste neutre
    assert reference_targets(CLOSES_B, F, S) == [0, 0, 0, 0, 0]


def test_longueur_et_valeurs():
    cibles = reference_targets(CLOSES_A, F, S)
    assert len(cibles) == 8
    for c in cibles:
        assert c in (0, 1)


def test_warmup():
    cibles = reference_targets(CLOSES_A, F, S)
    assert cibles[0] == 0
    assert cibles[1] == 0


def test_causalite():
    cibles = reference_targets(CLOSES_A, F, S)
    for i in range(len(CLOSES_A)):
        # on multiplie par 10 toutes les clotures apres i
        closes = CLOSES_A[: i + 1] + [c * 10 for c in CLOSES_A[i + 1 :]]
        modifiees = reference_targets(closes, F, S)
        assert modifiees[: i + 1] == cibles[: i + 1]


def test_cas_c():
    # egalite en position longue (12 contre 12 en 3) : pas une sortie, seul un croisement strict sort
    assert reference_targets([10, 10, 12, 12, 11], F, S) == [0, 0, 1, 1, 0]
