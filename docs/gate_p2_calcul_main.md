# Gate P2 - calcul a la main
Capital 1000 USDT, f = 0.001, s = 0.0005. Calcul fait a la calculatrice, sans IA.
## Entrees (t numerote de 1 a 10 ; dans le code, index = t - 1)
| t  | open | close | cible decidee au close |
|----|------|-------|------------------------|
| 1  | 100  | 101   | 0 |
| 2  | 101  | 102   | 1 |
| 3  | 102  | 105   | 1 |
| 4  | 105  | 108   | 1 |
| 5  | 108  | 107   | 0 |
| 6  | 110  | 109   | 0 |
| 7  | 109  | 105   | 1 |
| 8  | 104  | 102   | 1 |
| 9  | 102  | 98    | 1 |
| 10 | 98   | 100   | 1 |

## Execution 1 - achat, open t3 (cible 1 decidee au close t2)
prix_achat_1 = 102 x 1.0005 = 102.051
qty_btc_1 = 1000 x 0.999 / prix_achat_1 = 9.789223035541053

## Execution 2 - vente, open t6 (cible 0 decidee au close t5)
prix_vente_1 = 110 x 0.9995 = 109.945
brut_1 = qty_btc_1 x prix_vente_1 = 1076.276126642561
cash_apres_trade_1 = brut_1 x 0.999 = 1075.199850515919
trade 1 net = cash_apres_trade_1 - 1000 = 75.19985051591851

## Execution 3 - achat, open t8 (cible 1 decidee au close t7)
prix_achat_2 = 104 x 1.0005 = 104.052
qty_btc_2 = cash_apres_trade_1 x 0.999 / prix_achat_2 = 10.32296016093302

## Execution 4 - vente forcee, close t10 (fin des donnees, cible t10 ignoree)
prix_vente_2 = 100 x 0.9995 = 99.95
brut_2 = qty_btc_2 x prix_vente_2 = 1031.779868085255
cash_final = brut_2 x 0.999 = 1030.74808821717
trade 2 net = cash_final - cash_apres_trade_1 = -44.45176229874926

## Bilan
trades = 2
capital final = cash_final = 1030.74808821717