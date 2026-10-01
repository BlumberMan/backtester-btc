from dataclasses import dataclass


@dataclass
class Trade:
    """Un trade = une entrée + la sortie correspondante.
    pnl = cash après la vente moins cash avant l'achat, donc frais et slippage des deux jambes inclus."""
    entry_time: int
    entry_price: float
    exit_time: int
    exit_price: float
    qty_btc: float
    pnl: float


@dataclass
class Result:
    """Sortie du moteur : capital final en USDT et liste des trades fermés."""
    final_cash: float
    trades: list[Trade]


def run_backtest(candles, targets, fee=0.001, slippage=0.0005, initial_cash=1000.0):
    """Simule les trades long/neutre à partir des bougies (open_time, open, high, low, close) et d'une cible 0/1 par bougie.
    targets[t] est décidé à la clôture de t, donc exécuté à l'open de t+1 : le close de t est déjà passé,
    exécuter dessus serait du lookahead. La cible de la dernière bougie n'a pas de t+1, elle est ignorée."""
    if len(targets) != len(candles):
        raise ValueError(f"{len(targets)} cibles pour {len(candles)} bougies")
    for t, target in enumerate(targets):
        if target not in (0, 1):
            raise ValueError(f"cible invalide en t={t} : {target!r} (attendu 0 ou 1)")

    cash = initial_cash
    qty_btc = 0.0
    position = 0
    trades = []
    entry = None  # (entry_time, entry_price, qty_btc, cash_avant_achat) tant qu'une position est ouverte

    for t in range(1, len(candles)):
        target = targets[t - 1]
        if target == position:
            continue
        open_time, open_price = candles[t][0], candles[t][1]
        if target == 1:
            price = open_price * (1 + slippage)
            entry = (open_time, price, cash * (1 - fee) / price, cash)
            qty_btc = entry[2]
            cash = 0.0
        else:
            price = open_price * (1 - slippage)
            cash = qty_btc * price * (1 - fee)
            trades.append(_close_trade(entry, open_time, price, cash))
            qty_btc = 0.0
            entry = None
        position = target

    if position == 1:
        # Plus de bougie t+1 : on sort au close de la dernière, seul prix encore connu.
        last_time, last_close = candles[-1][0], candles[-1][4]
        price = last_close * (1 - slippage)
        cash = qty_btc * price * (1 - fee)
        trades.append(_close_trade(entry, last_time, price, cash))

    return Result(cash, trades)


def _close_trade(entry, exit_time, exit_price, cash_after):
    """Construit le Trade à partir de l'entrée mémorisée et du cash obtenu après la vente."""
    entry_time, entry_price, qty_btc, cash_before = entry
    return Trade(entry_time, entry_price, exit_time, exit_price, qty_btc, cash_after - cash_before)
