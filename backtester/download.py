import csv
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = "https://api.binance.com"
SYMBOL = "BTCUSDT"
INTERVAL = "4h"
START = datetime(2021, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 9, 1, tzinfo=timezone.utc)  # exclusive

LIMIT = 1000
INTERVAL_MS = 4 * 60 * 60 * 1000
OUTPUT_PATH = Path("data") / "raw" / "BTCUSDT_4h_raw.csv"
HEADER = ["open_time", "open", "high", "low", "close", "volume"]


def to_ms(dt):
    """Convertit un datetime UTC en millisecondes depuis l'epoch, l'unité attendue par Binance."""
    return int(dt.timestamp() * 1000)


def fetch_page(start_ms, end_ms, limit=LIMIT):
    """Fait un seul appel GET /api/v3/klines et retourne la liste brute de Binance.
    raise_for_status() fait échouer bruyamment plutôt que d'écrire des données fausses."""
    params = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": limit,
    }
    response = requests.get(f"{BASE_URL}/api/v3/klines", params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def download_klines(start_ms, end_ms, fetch_page=fetch_page):
    """Enchaîne les pages jusqu'à une page vide ou incomplète et exclut open_time >= end_ms.
    fetch_page est injectée pour que les tests remplacent le réseau par une fausse source."""
    klines = []
    next_start = start_ms
    while True:
        page = fetch_page(next_start, end_ms, LIMIT)
        if not page:
            break
        klines.extend(row for row in page if row[0] < end_ms)
        if len(page) < LIMIT:
            break
        next_start = page[-1][0] + INTERVAL_MS
    return klines


def parse_kline(row):
    """Garde les 6 premiers champs d'une bougie Binance (qui en a 12).
    Prix et volume restent des chaînes : pas de float, donc aucune perte de précision."""
    return (int(row[0]), row[1], row[2], row[3], row[4], row[5])


def write_csv(rows, path):
    """Écrit l'en-tête puis les bougies en CSV, en créant le dossier parent si besoin.
    lineterminator="\\n" force des fins de ligne LF : fichier identique octet par octet sur tout OS."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(HEADER)
        writer.writerows(rows)


def main():
    """Télécharge toute la période, écrit le CSV brut et affiche un résumé pour vérifier."""
    raw = download_klines(to_ms(START), to_ms(END))
    rows = [parse_kline(row) for row in raw]
    write_csv(rows, OUTPUT_PATH)
    print(f"{len(rows)} bougies écrites dans {OUTPUT_PATH}")
    if rows:
        print(f"Premier open_time : {rows[0][0]}")
        print(f"Dernier open_time : {rows[-1][0]}")


if __name__ == "__main__":
    main()
