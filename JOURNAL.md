# Journal

2026-09-28 — P0 en cours. Fait : repo GitHub, SPEC.md v1 (Binance spot, 4h, UTC, Python 3.14, train/test figés, gate P3 chiffré), BACKLOG.md, squelette (package backtester, 4 tests pytest OK, requirements.txt épinglé, README).
Leçons : git status avant chaque commit (SPEC oubliée hors staging) ; le message de commit décrit le diff, rien d'autre.
Prochaine étape : gate P0 = clone + install + pytest sur un laptop vierge, sortie brute à coller.
2026-09-29 — P0 VALIDÉ. Fait : .gitignore réparé (espaces en tête = aucune règle active) + \_\_pycache\_\_ retirés du suivi (7b69ba4) ; prérequis dans le README (f801323) ; CI GitHub Actions sur Windows vierge (e0b65f8) : Python 3.14.7, 4 passed, working tree clean.

Leçons : "Everything up-to-date" au push = commit oublié ; relire tout fichier produit par l'agent, même le .gitignore ; un fichier généré n'entre jamais dans Git ; un test sur la machine d'origine ne prouve rien.

Prochaine étape : P1 — d'abord .gitattributes (fins de ligne), puis module de téléchargement des bougies BTC/USDT 4h.

2026-09-29 (session 3) — P1 en cours. Fait : .gitattributes LF (ead8f29) ; module download.py (pagination Binance /api/v3/klines, END exclusif, prix gardés en chaînes, CSV en LF) + 5 tests, requests==2.34.2 épinglé. 9 passed.

Leçons : la commande de test est python -m pytest -v (pytest seul ne trouve pas le package, la CI fait foi) ; endTime Binance est inclusif, d'où le filtre < END ; csv écrit \\r\\n par défaut ; un test vert peut ne rien vérifier, relire le fichier de tests.

Prochaine étape : téléchargement réel ×2 depuis la racine du repo + hash SHA-256 des deux fichiers, puis module clean (trous, doublons, UTC) → gate P1.

2026-09-30 (session 4) — P1 en cours. Fait : download réel ×2, hash identiques (brut 5d9e32da…) ; module clean.py (dedupe strict, validation OHLC en Decimal, find\_gaps sans comblement, datetime\_utc) + 12 tests, 21 passed ; 12 414 bougies, 0 doublon, 0 trou, 0 volume nul, hash propre 299fb0ec… ×2 ; hash de référence dans le README.

Leçons : pas de (.venv) dans le prompt = Python système, sans les dépendances ; une commande plante → on arrête la série et on colle l'erreur ; un nettoyage qui plante laisse l'ancien fichier sur le disque, ne jamais s'y fier.

Prochaine étape : gate P1 = clone neuf dans un autre dossier, un autre jour, download + clean, les deux hash doivent correspondre au README.

2026-09-30 (session 4 bis) — Gate P1, partie clone neuf OK : clone dans %TEMP%, venv neuf, 21 passed, hash brut 5d9e32da… et propre 299fb0ec… identiques au README.

Leçons : les hash de référence sont dans le README ; toute régénération des données se vérifie contre eux, sinon on arrête tout.

Prochaine étape : début de prochaine session (autre jour) : download + clean + 2 certutil → si identiques, P1 VALIDÉ, puis ouverture de P2.

2026-10-01 (session 5) — P1 VALIDÉ (autre jour, data supprimée avant, hash identiques au README). P2 : SPEC moteur (5030b11), calcul à la main de référence commité avant le code (762f8a5, capital final 1030.74808821717, 2 trades), engine.py + 9 tests, 30 passed ; gate P2 validé si CI verte.
Leçons : le Bloc-notes réécrit le Markdown → VS Code pour les .md ; un diff plus large que prévu ne se commite pas ; un calcul de référence fait par un LLM ne vaut rien → fait à la calculatrice ; vérifier l'ordre de grandeur avant d'écrire un chiffre ; un test anti-lookahead doit utiliser des données où close[t] != open[t+1].
Prochaine étape : ouvrir P3 — d'abord régler l'item BACKLOG « test regardé une seule fois » (mécanisme avant toute stratégie), puis module de chargement du CSV propre et découpe train/test.
2026-10-01 (session 6) — P2 VALIDÉ (calcul à la main 762f8a5 avant le code 1749756, test sur la valeur de référence). P3 : infra complète, SPEC règles complémentaires + interface stratégie, gate.py, lock.py, holdout.py, runner.py (liste blanche d'imports, check_causality au train), 139 tests ; CI vue verte jusqu'à 67f5d66, d1a677a vu vert en CI #27.
Leçons : une valeur de référence se calcule à la calculatrice, dans l'ordre (jours en ms avant d'ajouter au timestamp) ; preuves collées en entier, jamais « c'est bon » ; le contrôle de causalité par préfixes ne couvre que quelques index, le test anti-lookahead écrit à la main reste obligatoire.
Prochaine étape : choisir UNE idée, la valider avec moi en 3 phrases, puis écrire docs/strategies/<nom>.md avant tout code ; ensuite P3-4e (balayage des combinaisons).
2026-10-01 (session 6 bis) — P3 : strategie donchian ecrite avant le code (696083c), regle de choix fixee (voisines), exception au calcul a la main -> reference naive separee (8e408ed, e6c12c4), SPEC plantage et demarrage neutre (d4b51a5), hash des donnees verifie au train et au test + check_causality aux points de decision (7bcf233), donchian.py egal a la reference sur 3200 cas, 156 tests.
Lecons : une IA qui propose des strategies a pu voir 2024-2026 -> idee classique et section Transparence ; calcul a la main seulement pour une logique nouvelle ou un chiffre de gate ; quand je bloque, je le dis et on decide une exception ecrite au lieu de sauter l'etape.
Prochaine etape : P3-4e, balayage des 9 combinaisons sur le train (sans calcul a la main), puis application de la regle de choix telle qu'ecrite.

2026-10-03 (session 7) — P3 : sweep.py + 14 tests (29cfe91, 170 passed), balayage des 9 combinaisons donchian sur le train : AUCUNE retenue (1 seule combinaison à ≥ 30 trades, elle perd), idée abandonnée, ne compte pas dans la condition d'arrêt (0/3).
Leçons : c1 (30 trades) est le verrou en 4h sur 3 ans, estimer le nombre de trades possible avant d'écrire une idée ; un bon capital avec 10 trades ne prouve rien ; l'abandon s'applique tel qu'écrit, sans variante.
Prochaine étape : choisir UNE nouvelle idée, la valider avec moi en 3 phrases dont une estimation du nombre de trades, puis docs/strategies/<nom>.md avant tout code.