# Backlog

- [ ] Definir le critere chiffre du gate P4 (avant de demarrer P4).
- [ ] Trouver un mecanisme pour garantir que la periode de test n'est regardee qu'une fois (P3).
- [ ] Si api.binance.com est bloque (reseau, pays) : basculer BASE_URL sur https://data-api.binance.vision (endpoint donnees de marche uniquement). Test IUT du 30/09 : hash identiques selon un rapport, sans sortie brute, donc non prouve.
- Renforcer check_causality : beaucoup plus de coupures (ex. 200 réparties) avant la première stratégie sérieuse.
- test_engine : tests frais seuls et slippage seul, valeurs calculées à la main ; assert redondant abs=0.01 / 1e-6.
- FEE et SLIPPAGE dupliqués entre engine.py (défauts) et gate.py.
- clean/data/holdout : logique de grille dupliquée.
- load_strategy : @dataclass dans une stratégie peut planter (module absent de sys.modules).
- WARMUP > 6570 ne plante qu'au test ; DATA_PATH et RESULTS_PATH relatifs (lancer depuis la racine).
- lock : pas de test avec "ema\n" ni avec git en échec ; résultats supprimés non détectés par le verrou.
- Lancer toujours `train` avant de geler : un plantage au test consomme le run.