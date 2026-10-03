# donchian

## Idee en une phrase
J'achete quand la cloture depasse le plus haut des N dernieres bougies, et je repasse en cash quand elle passe sous le plus bas des M dernieres.

## Pourquoi ca pourrait marcher
Les grosses tendances durent parce que l'argent et l'information arrivent progressivement. Un prix qui sort de sa fourchette recente est souvent le debut d'un mouvement qui continue. Sortir sous le plus bas recent permet d'eviter une partie des grosses baisses. C'est une hypothese, pas une preuve.

## Regles
- Signal evalue a la cloture de chaque bougie 4h, execute a l'open suivant (moteur).
- Entree : cloture strictement superieure au plus grand high des N bougies precedentes (la bougie actuelle n'est pas comptee).
- Sortie : cloture strictement inferieure au plus petit low des M bougies precedentes (la bougie actuelle n'est pas comptee).
- Etat neutre : cible 1 si la condition d'entree est vraie, sinon 0.
- Etat long : cible 0 si la condition de sortie est vraie, sinon 1.
- Les WARMUP premieres bougies : cible 0.
- Pas de short, pas de levier.

## Parametres
| nom | role | valeurs possibles |
|-----|------|-------------------|
| N | bougies pour le plus haut d'entree (10, 20 ou 40 jours) | 60, 120, 240 |
| M | bougies pour le plus bas de sortie (5, 10 ou 20 jours) | 30, 60, 120 |

## WARMUP
WARMUP = max(N, M), parce qu'il faut N bougies pour le plus haut d'entree et M pour le plus bas de sortie.

## Combinaisons a tester sur le train (9)
1. N=60, M=30
2. N=60, M=60
3. N=60, M=120
4. N=120, M=30
5. N=120, M=60
6. N=120, M=120
7. N=240, M=30
8. N=240, M=60
9. N=240, M=120

## Regle de choix
Les voisines d'une combinaison sont celles qui different d'un seul cran en N ou en M dans la grille (pas en diagonale). On retient une combinaison qui passe les 4 criteres ET dont toutes les voisines passent aussi les 4 criteres. S'il y en a plusieurs, on prend celle au capital final le plus eleve parmi elles. S'il n'y en a aucune, l'idee est abandonnee. Cette regle est fixee avant tout resultat et ne change pas.

## Ce qui prouverait que l'idee est fausse
Aucune combinaison ne satisfait la regle de choix : soit aucune ne passe les 4 criteres, soit les combinaisons qui passent sont isolees, soit il y a moins de 30 trades partout. L'idee est alors abandonnee, sans nouvelle combinaison ni filtre ajoute. Un echec au train ne compte pas dans la condition d'arret.

## Transparence
Idee proposee apres consultation d'une IA ayant probablement vu des prix 2024-2026. Choisie parce que classique (Turtles, annees 1980) avec parametres standards convertis en bougies 4h, pas tuned. Si le test passe, la preuve est plus faible qu'une idee nee a froid. Ecart avec les Turtles : eux entraient pendant la bougie, des que le prix touchait le record. Ici le signal est decide a la cloture et execute a l'open de la bougie suivante (seul mode du moteur). Ce n'est donc pas exactement la strategie classique.

## Resultats train
Commit 29cfe91, python -m backtester.sweep, donnees verifiees par hash.

   n    m n_trades  final_normal final_doubled      final_bh    c1    c2    c3    c4 passed
  60   30       36        799.87        717.91       1439.86  True False False False  False
  60   60       24       1390.56       1293.87       1439.86 False  True  True False  False
  60  120       18       1289.32       1221.48       1439.86 False  True  True False  False
 120   30       22       1411.60       1321.36       1439.86 False  True  True False  False
 120   60       16       1830.56       1744.68       1439.86 False  True  True  True  False
 120  120       10       2679.32       2600.06       1439.86 False  True  True  True  False
 240   30       18        856.71        811.63       1439.86 False False False False  False
 240   60       14        978.79        938.49       1439.86 False False False False  False
 240  120        9       1702.32       1656.93       1439.86 False  True  True  True  False
AUCUNE : idee abandonnee

Verdict : aucune combinaison ne satisfait la regle de choix (une seule combinaison atteint 30 trades, elle perd de l'argent). Idee donchian abandonnee, sans nouvelle combinaison ni filtre. Ne compte pas dans la condition d'arret (echec au train).