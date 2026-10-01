# Gate P3 - calcul a la main (buy and hold, 4 bougies)

Capital 1000 USDT, f = 0.001, s = 0.0005. Calcul fait a la calculatrice, sans IA.

## Entrees (t numerote de 1 a 4 ; dans le code, index = t - 1)

| t | open | close | cible decidee au close |
|---|------|-------|------------------------|
| 1 | 100  | 100.5 | 1 |
| 2 | 101  | 102   | 1 |
| 3 | 102  | 105   | 1 |
| 4 | 105  | 107   | 1 |

## Execution 1 - achat, open t2 (cible 1 decidee au close t1)

prix_achat = 101 x 1.0005 = 101.0505
qty_btc = 1000 x 0.999 / prix_achat = 9.886146035892945

## Execution 2 - vente forcee, close t4 (fin des donnees, cible t4 ignoree)

prix_vente = 107 x 0.9995 = 106.9465
brut = qty_btc x prix_vente = 1057.288717027625
cash_final = brut x 0.999 = 1056.231428310597

## Bilan

trades = 1
buy and hold final = 1056.231428310597