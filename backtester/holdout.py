import csv
from collections import deque

from backtester.clean import to_utc_str
from backtester.data import STEP_MS, TRAIN_END_MS, TRAIN_START_MS

TEST_START_MS = TRAIN_END_MS  # 2024-01-01T00:00:00Z, inclus : le test commence exactement là où le train s'arrête
TEST_END_MS = 1788220800000  # 2026-09-01T00:00:00Z, exclu
TEST_COUNT = 5844  # 974 jours x 6 bougies

_TRAIN_COUNT = (TRAIN_END_MS - TRAIN_START_MS) // STEP_MS  # 6570 : plafond du WARMUP


def load_test(path, warmup):
    """Lit le CSV propre et retourne (warmup_candles, test_candles), tuples (open_time, open, high, low, close).
    Cette fonction n'est appelée que par la commande de test, une seule fois par stratégie : la période de test
    ne doit être regardée qu'une fois, donc rien d'autre dans le code ne doit pouvoir charger ces bougies.

    warmup_candles = les `warmup` dernières bougies du train : la stratégie en a besoin pour calculer ses
    indicateurs dès la première bougie du test, avec des cibles forcées à 0 par l'appelant. Seules ces
    bougies sont gardées en mémoire (deque bornée), le reste du train est lu pour vérifier la grille puis oublié.
    test_candles = les bougies avec TEST_START_MS <= open_time < TEST_END_MS.

    La lecture s'arrête à la première ligne avec open_time >= TEST_END_MS, sans en convertir les prix :
    les données postérieures à la période n'ont pas à être lues, et une ligne abîmée au-delà ne doit pas
    faire planter (donc consommer) le run test.

    Lève ValueError si :
    - warmup n'est pas un entier >= 0 ou dépasse 6570 : on ne peut pas fournir plus d'historique que le train
      n'en contient, et un warmup négatif ou non entier est un bug de la stratégie, pas une valeur à corriger ;
    - la première bougie n'est pas TRAIN_START_MS, ou un trou ou un doublon apparaît, y compris à la jonction
      train/test : la grille doit être continue pour que les bougies de warmup précèdent immédiatement le test
      et qu'une cible décidée en t s'exécute bien à l'open de t+1 ;
    - la dernière bougie test n'est pas TEST_END_MS - STEP_MS ou il n'y a pas TEST_COUNT bougies test : un test
      tronqué donnerait un résultat sur une autre période que celle de la SPEC, et ce résultat serait définitif."""
    if type(warmup) is not int or not 0 <= warmup <= _TRAIN_COUNT:
        raise ValueError(f"warmup {warmup!r} invalide : entier attendu entre 0 et {_TRAIN_COUNT}")

    warmup_candles = deque(maxlen=warmup)
    test_candles = []
    expected = TRAIN_START_MS
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)  # en-tête
        for row in reader:
            open_time = int(row[0])
            if open_time >= TEST_END_MS:
                break
            if open_time != expected:
                raise ValueError(
                    f"open_time {open_time} ({to_utc_str(open_time)}) au lieu de {expected} ({to_utc_str(expected)})"
                )
            expected += STEP_MS
            candle = (open_time, float(row[2]), float(row[3]), float(row[4]), float(row[5]))
            if open_time < TEST_START_MS:
                warmup_candles.append(candle)
            else:
                test_candles.append(candle)

    _check_test_complete(test_candles)
    return list(warmup_candles), test_candles


def _check_test_complete(test_candles):
    """Vérifie que le test va jusqu'à la dernière bougie de la période et en contient exactement TEST_COUNT.
    La grille est déjà vérifiée pendant la lecture, mais un fichier qui s'arrête trop tôt passe ce contrôle :
    c'est ici qu'on le refuse."""
    last = test_candles[-1][0] if test_candles else None
    if last != TEST_END_MS - STEP_MS or len(test_candles) != TEST_COUNT:
        last_str = "aucune" if last is None else f"{last} ({to_utc_str(last)})"
        raise ValueError(
            f"test incomplet : {len(test_candles)} bougies au lieu de {TEST_COUNT}, dernière bougie {last_str}"
        )
