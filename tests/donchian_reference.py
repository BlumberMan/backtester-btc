"""Reference naive de la strategie donchian, ecrite a partir de docs/strategies/donchian.md uniquement."""


def reference_targets(highs, lows, closes, n, m):
    """Renvoie la liste des cibles (0 ou 1), une par bougie."""
    warmup = n if n > m else m  # WARMUP = max(N, M), ecrit sans max()
    long = False  # au depart on est en cash
    cibles = []
    for i in range(len(closes)):
        if i < warmup:
            # pas assez de bougies avant i : cible 0, on reste en cash
            cibles.append(0)
            continue
        if not long:
            # record = plus grand high des n bougies precedentes (i-n a i-1, la bougie i exclue)
            record = highs[i - n]
            for j in range(i - n + 1, i):
                if highs[j] > record:
                    record = highs[j]
            if closes[i] > record:  # strictement au-dessus : on entre
                long = True
        else:
            # plancher = plus petit low des m bougies precedentes (i-m a i-1, la bougie i exclue)
            plancher = lows[i - m]
            for j in range(i - m + 1, i):
                if lows[j] < plancher:
                    plancher = lows[j]
            if closes[i] < plancher:  # strictement en dessous : on sort
                long = False
        if long:
            cibles.append(1)
        else:
            cibles.append(0)
    return cibles
