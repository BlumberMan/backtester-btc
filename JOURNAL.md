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

