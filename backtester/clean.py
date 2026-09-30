import csv
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from backtester.download import END, INTERVAL_MS, START, to_ms

RAW_PATH = Path("data") / "raw" / "BTCUSDT_4h_raw.csv"
CLEAN_PATH = Path("data") / "BTCUSDT_4h.csv"
CLEAN_HEADER = ["open_time", "datetime_utc", "open", "high", "low", "close", "volume"]


def read_raw(path):
    """Lit le CSV brut (en-tête ignoré) et retourne des tuples (open_time, open, high, low, close, volume).
    Seul open_time est converti en int ; prix et volume restent des chaînes pour ne rien perdre."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        return [(int(r[0]), r[1], r[2], r[3], r[4], r[5]) for r in reader]


def dedupe(rows):
    """Trie par open_time et retire les doublons strictement identiques.
    Deux valeurs différentes pour un même open_time : impossible de savoir laquelle est juste, donc on lève."""
    kept = {}
    removed = 0
    for row in rows:
        existing = kept.get(row[0])
        if existing is None:
            kept[row[0]] = row
        elif existing == row:
            removed += 1
        else:
            raise ValueError(f"open_time {row[0]} en double avec des valeurs différentes")
    return [kept[t] for t in sorted(kept)], removed


def validate(rows, start_ms, end_ms):
    """Lève ValueError sur un open_time hors grille ou hors [start_ms, end_ms[, ou une bougie incohérente.
    Les comparaisons se font en Decimal construit depuis les chaînes : exact, contrairement à float."""
    for open_time, o, h, l, c, v in rows:
        if open_time % INTERVAL_MS != 0:
            raise ValueError(f"open_time {open_time} n'est pas un multiple de 4h")
        if open_time < start_ms or open_time >= end_ms:
            raise ValueError(f"open_time {open_time} hors de la période [{start_ms}, {end_ms}[")
        o, h, l, c, v = (Decimal(x) for x in (o, h, l, c, v))
        if l > min(o, c) or h < max(o, c) or l <= 0 or v < 0:
            raise ValueError(f"bougie incohérente à open_time {open_time}")


def find_gaps(rows, start_ms, end_ms):
    """Retourne les open_time attendus sur la grille [start_ms, end_ms[ mais absents des données.
    On signale seulement : combler un trou reviendrait à inventer des prix."""
    present = {row[0] for row in rows}
    return [t for t in range(start_ms, end_ms, INTERVAL_MS) if t not in present]


def count_zero_volume(rows):
    """Compte les bougies à volume nul (ex. marché à l'arrêt) sans les rejeter : elles sont réelles."""
    return sum(1 for row in rows if Decimal(row[5]) == 0)


def to_utc_str(open_time_ms):
    """Formate un open_time en "YYYY-MM-DDTHH:MM:SSZ" UTC.
    Division entière pour éviter tout float, tz=UTC pour ne jamais dépendre de l'heure locale."""
    return datetime.fromtimestamp(open_time_ms // 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_clean(rows, path):
    """Écrit le CSV propre avec une colonne datetime_utc lisible, mêmes garanties que download.write_csv.
    Les chaînes de prix et volume sont recopiées telles quelles : fichier reproductible octet par octet."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(CLEAN_HEADER)
        for open_time, o, h, l, c, v in rows:
            writer.writerow([open_time, to_utc_str(open_time), o, h, l, c, v])


def main():
    """Lit le brut, dédoublonne, valide, cherche les trous, écrit le fichier propre et affiche un résumé."""
    start_ms, end_ms = to_ms(START), to_ms(END)
    raw = read_raw(RAW_PATH)
    rows, removed = dedupe(raw)
    validate(rows, start_ms, end_ms)
    gaps = find_gaps(rows, start_ms, end_ms)
    write_clean(rows, CLEAN_PATH)

    print(f"Bougies lues : {len(raw)}")
    print(f"Doublons retirés : {removed}")
    print(f"Trous : {len(gaps)}")
    for t in gaps[:10]:
        print(f"  {to_utc_str(t)}")
    print(f"Bougies à volume nul : {count_zero_volume(rows)}")
    print(f"Bougies écrites dans {CLEAN_PATH} : {len(rows)}")
    if rows:
        print(f"Premier datetime_utc : {to_utc_str(rows[0][0])}")
        print(f"Dernier datetime_utc : {to_utc_str(rows[-1][0])}")


if __name__ == "__main__":
    main()
