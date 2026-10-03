"""Reference naive de la strategie sma-cross, ecrite a partir de docs/strategies/sma-cross.md uniquement."""


def sma(closes, n, i):
    """Moyenne des n dernieres clotures, bougie i comprise (sa cloture est connue a la decision)."""
    total = 0
    for j in range(i - n + 1, i + 1):
        # on additionne les clotures une par une, sans sum() ni tranche
        total = total + closes[j]
    return total / n


def reference_targets(closes, f, s):
    """Renvoie la liste des cibles (0 ou 1), une par bougie."""
    warmup = s  # WARMUP = S : il faut la SMA lente aux index i-1 et i, ecrit sans max()
    long = False  # au depart on est neutre (en cash)
    cibles = []
    for i in range(len(closes)):
        if i < warmup:
            # pas assez de bougies pour la SMA lente en i-1 : cible 0, on reste neutre
            cibles.append(0)
            continue
        rapide_avant = sma(closes, f, i - 1)
        lente_avant = sma(closes, s, i - 1)
        rapide = sma(closes, f, i)
        lente = sma(closes, s, i)
        if not long:
            # croisement strict a la hausse : la rapide etait en dessous ou egale, elle passe au-dessus
            if rapide_avant <= lente_avant and rapide > lente:
                long = True
        else:
            # croisement strict a la baisse : la rapide etait au-dessus ou egale, elle passe en dessous
            if rapide_avant >= lente_avant and rapide < lente:
                long = False
        # sinon l'etat ne change pas, la cible reste celle de l'etat courant
        if long:
            cibles.append(1)
        else:
            cibles.append(0)
    return cibles
