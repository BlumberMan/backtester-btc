"""Strategie sma-cross : long quand la SMA rapide croise strictement au-dessus de la SMA lente,
retour en cash quand elle recroise strictement en dessous.

Regles, parametres et grille de combinaisons : docs/strategies/sma-cross.md.
"""

# Valeurs provisoires du centre de la grille : la combinaison retenue sera fixee apres le train.
F = 60
S = 180

# Il faut la SMA lente aux index i-1 et i : sa fenetre en i-1 commence a l'index 0 quand i = S.
WARMUP = S


def sma(closes, n, i):
    """Moyenne des n dernieres clotures, bougie i comprise (sa cloture est connue a la decision).

    Somme recalculee sur toute la fenetre, de i-n+1 a i, dans cet ordre et en partant de 0 : le
    meme calcul que tests/sma_cross_reference.py, donc un resultat identique bit a bit. Pas de
    somme glissante (les erreurs d'arrondi s'accumuleraient differemment) ni de sum() : depuis
    Python 3.12, sum() sur des floats compense les arrondis et peut donner un autre dernier bit.
    """
    total = 0
    for j in range(i - n + 1, i + 1):
        total = total + closes[j]
    return total / n


def sma_cross_targets(candles, f, s):
    """Retourne une cible 0 ou 1 par bougie, avec f bougies pour la SMA rapide et s pour la lente."""
    # candles = tuples (open_time, open, high, low, close) : seule la cloture est lue.
    closes = [c[4] for c in candles]

    targets = []
    long = False  # etat de la machine : True si on detient du BTC, neutre au debut de la periode
    for i in range(len(candles)):
        if i < s:
            # Pas encore assez de bougies pour la SMA lente en i-1.
            targets.append(0)
            continue
        if i == s:
            # Premiere decision : les SMA en i-1 n'ont pas encore ete calculees.
            rapide_avant = sma(closes, f, i - 1)
            lente_avant = sma(closes, s, i - 1)
        rapide = sma(closes, f, i)
        lente = sma(closes, s, i)
        if not long:
            # Croisement strict a la hausse : en dessous ou egale en i-1, strictement au-dessus en i.
            if rapide_avant <= lente_avant and rapide > lente:
                long = True
        else:
            # Croisement strict a la baisse : au-dessus ou egale en i-1, strictement en dessous en i.
            if rapide_avant >= lente_avant and rapide < lente:
                long = False
        targets.append(1 if long else 0)
        # Les SMA en i servent de SMA en i-1 a la bougie suivante : meme fenetre, meme ordre de
        # somme, donc la meme valeur que si on la recalculait. Ce n'est pas une somme glissante.
        rapide_avant, lente_avant = rapide, lente
    return targets


def compute_targets(candles):
    return sma_cross_targets(candles, F, S)
