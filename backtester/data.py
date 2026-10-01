import csv

from backtester.clean import to_utc_str

TRAIN_START_MS = 1609459200000  # 2021-01-01T00:00:00Z, inclus
TRAIN_END_MS = 1704067200000  # 2024-01-01T00:00:00Z, exclu : premier open_time du test
STEP_MS = 14400000  # 4h en millisecondes


def load_train(path):
    """Lit le CSV propre et retourne les bougies du train (open_time, open, high, low, close), format du moteur.
    La lecture s'arrête à la première ligne avec open_time >= TRAIN_END_MS, avant même d'en convertir les prix :
    le test ne doit être vu qu'une fois, par la commande de test, donc aucune bougie du test ne doit pouvoir
    passer par ici, même par erreur. Les lignes suivantes ne sont jamais analysées.
    Lève ValueError si la première bougie n'est pas TRAIN_START_MS, sur un trou ou un doublon, ou si aucune
    bougie du train n'est trouvée : un train tronqué ou décalé fausserait silencieusement le WARMUP, les
    indicateurs et les 4 critères du gate, il vaut mieux refuser de calculer."""
    candles = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)  # en-tête
        for row in reader:
            open_time = int(row[0])
            if open_time >= TRAIN_END_MS:
                break
            _check_next(candles, open_time)
            candles.append((open_time, float(row[2]), float(row[3]), float(row[4]), float(row[5])))
    if not candles:
        raise ValueError(f"aucune bougie du train dans {path}")
    return candles


def _check_next(candles, open_time):
    """Vérifie que open_time est exactement la bougie attendue après celles déjà lues.
    La première doit être TRAIN_START_MS : le prechauffage sur le train suppose que le dataset commence là.
    Ensuite le pas doit valoir STEP_MS : un trou ferait exécuter une cible sur un open qui n'est pas t+1,
    un doublon compterait deux fois la même bougie."""
    expected = TRAIN_START_MS if not candles else candles[-1][0] + STEP_MS
    if open_time != expected:
        raise ValueError(
            f"open_time {open_time} ({to_utc_str(open_time)}) au lieu de {expected} ({to_utc_str(expected)})"
        )
