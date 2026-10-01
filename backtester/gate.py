from backtester.engine import run_backtest

# Frais et slippage du moteur (SPEC, Moteur P2) : taux spot Binance standard, sans reduction BNB.
FEE = 0.001
SLIPPAGE = 0.0005
# Le critere 3 double les deux couts : une strategie qui ne survit qu'avec des couts exacts
# est trop fragile, le moindre ecart reel (spread, frais, latence) la ferait perdre.
FEE_DOUBLED = 0.002
SLIPPAGE_DOUBLED = 0.001
# En dessous de 30 trades, le resultat peut venir de quelques coups chanceux : trop peu
# d'echantillons pour distinguer un avantage reel du hasard.
MIN_TRADES = 30
INITIAL_CASH = 1000.0


def check_criteria(n_trades, final_normal, final_doubled, final_bh):
    """Applique les 4 criteres du gate P3. Fonction pure : ne lance aucun backtest.

    c1 : n_trades >= MIN_TRADES. Non strict : 30 trades est le minimum accepte, pas un seuil a depasser.
    c2 : final_normal > INITIAL_CASH, strict. Finir a 1000 pile, c'est n'avoir rien gagne :
         un resultat neutre est un echec (SPEC : "tout echec ou resultat neutre entraine l'abandon").
    c3 : final_doubled >= INITIAL_CASH, non strict. Avec couts doubles on ne demande pas de gain,
         seulement de ne pas perdre : c'est un test de robustesse, pas de rentabilite.
    c4 : final_normal > final_bh, strict. Egaler le buy and hold n'apporte rien : autant acheter
         et garder, sans le risque d'execution d'une strategie active.
    passed est vrai seulement si les 4 criteres sont vrais.
    """
    c1 = n_trades >= MIN_TRADES
    c2 = final_normal > INITIAL_CASH
    c3 = final_doubled >= INITIAL_CASH
    c4 = final_normal > final_bh
    return {"c1": c1, "c2": c2, "c3": c3, "c4": c4, "passed": c1 and c2 and c3 and c4}


def evaluate(candles, targets):
    """Lance les 3 backtests du gate P3 sur une periode et applique les criteres.

    Tout passe par run_backtest pour que le gate juge exactement ce que le moteur simule,
    sans second calcul qui pourrait diverger. Le buy and hold de reference est un run avec
    toutes les cibles a 1 et les couts normaux (SPEC) : meme moteur, memes couts, donc la
    comparaison c4 ne mesure que la valeur des decisions de la strategie.
    n_trades vient du run normal, celui qui represente les conditions reelles attendues.
    """
    normal = run_backtest(candles, targets, fee=FEE, slippage=SLIPPAGE, initial_cash=INITIAL_CASH)
    doubled = run_backtest(candles, targets, fee=FEE_DOUBLED, slippage=SLIPPAGE_DOUBLED, initial_cash=INITIAL_CASH)
    bh = run_backtest(candles, [1] * len(candles), fee=FEE, slippage=SLIPPAGE, initial_cash=INITIAL_CASH)

    result = {
        "n_trades": len(normal.trades),
        "final_normal": normal.final_cash,
        "final_doubled": doubled.final_cash,
        "final_bh": bh.final_cash,
    }
    result.update(check_criteria(result["n_trades"], normal.final_cash, doubled.final_cash, bh.final_cash))
    return result
