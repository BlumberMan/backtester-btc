# Donchian - reference

Exception decidee le 2026-10-01 : pas de calcul a la main complet pour Donchian.
La reference est la fonction naive tests/donchian_reference.py, ecrite dans une session Claude Code separee a partir de docs/strategies/donchian.md uniquement, commitee AVANT le code de la strategie et relue ligne par ligne.
Le code de la strategie est ecrit dans une autre session, qui n'ouvre pas tests/donchian_reference.py. Les tests comparent strategie et reference.
Limite : reference et strategie viennent du meme type d'outil, une mauvaise lecture commune de la regle passerait.
Seule valeur calculee a la main : i=3 -> cible 0 (close = record, pas d'entree).

N = 3, M = 2, WARMUP = 3.

| i | high | low | close |
|---|------|-----|-------|
| 0 | 10 | 8 | 9 |
| 1 | 11 | 9 | 10 |
| 2 | 12 | 10 | 11 |
| 3 | 12 | 10 | 12 |
| 4 | 14 | 11 | 13.5 |
| 5 | 15 | 12 | 14 |
| 6 | 14 | 11 | 11.5 |
| 7 | 12 | 9 | 9.5 |
| 8 | 11 | 9 | 10.5 |
| 9 | 17 | 10 | 16 |
| 10 | 16 | 8.5 | 9 |