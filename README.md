# backtester-btc

Backtester de stratégies de trading sur BTC/USDT, écrit en Python 3.14.

## Prérequis
Git et Python 3.14 installés.

## Installation (Windows)

```
git clone https://github.com/BlumberMan/backtester-btc.git
cd backtester-btc
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -v
python -m backtester
```
## Données

Depuis la racine du repo, venv activé :

```
python -m backtester.download
python -m backtester.clean
```

Résultat attendu (BTCUSDT spot 4h, 2021-01-01 00:00 → 2026-08-31 20:00 UTC, 12 414 bougies) :

- `data/raw/BTCUSDT_4h_raw.csv` — SHA-256 `5d9e32daef19a335285ab061fc36b1118adf31f955d3fd39c94b05f6ea45e525`
- `data/BTCUSDT_4h.csv` — SHA-256 `299fb0ec948f43df270dc162659388f5b6b87152501cc7212f5b57e9424dd1fa`