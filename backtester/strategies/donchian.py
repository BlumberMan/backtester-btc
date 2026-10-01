"""Strategie donchian : achat sur cassure du plus haut des N dernieres bougies, retour en cash
sous le plus bas des M dernieres.

Regles, parametres et grille de combinaisons : docs/strategies/donchian.md.
"""

# Valeurs provisoires du centre de la grille : la combinaison retenue sera fixee apres le train.
N = 120
M = 60

# Il faut N bougies precedentes pour le record d'entree et M pour le plancher de sortie.
WARMUP = max(N, M)


def donchian_targets(candles, n, m):
    """Retourne une cible 0 ou 1 par bougie, avec n bougies pour l'entree et m pour la sortie."""
    # candles = tuples (open_time, open, high, low, close) : on extrait les colonnes une fois.
    highs = [c[2] for c in candles]
    lows = [c[3] for c in candles]
    closes = [c[4] for c in candles]

    targets = []
    long = False  # etat de la machine : True si on detient du BTC, False si on est en cash
    for i in range(len(candles)):
        if i < max(n, m):
            # Pas encore assez de bougies precedentes pour calculer record et plancher.
            targets.append(0)
            continue
        if not long:
            # Plus haut des n bougies precedentes, la bougie i n'est pas comptee.
            record = max(highs[i - n:i])
            # Entree seulement si la cloture depasse strictement le record (egalite : rien).
            if closes[i] > record:
                long = True
        else:
            # Plus bas des m bougies precedentes, la bougie i n'est pas comptee.
            plancher = min(lows[i - m:i])
            # Sortie seulement si la cloture passe strictement sous le plancher (egalite : rien).
            if closes[i] < plancher:
                long = False
        targets.append(1 if long else 0)
    return targets


def compute_targets(candles):
    return donchian_targets(candles, N, M)
