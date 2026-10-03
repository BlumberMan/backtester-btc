# sma-cross

## Idee en une phrase
Je passe long quand la SMA rapide croise strictement au-dessus de la SMA lente, et je repasse en cash quand elle recroise strictement en dessous.

## Pourquoi ca pourrait marcher
Meme hypothese que donchian : les tendances de BTC persistent, car l'information et le capital arrivent progressivement. Ce n'est pas une famille differente, seulement une autre regle de decision. C'est une hypothese, pas une preuve.

## Regles
- Signal evalue a la cloture de chaque bougie 4h, execute a l'open suivant (moteur).
- SMA(n)[i] = moyenne des n dernieres clotures, bougie i comprise (la cloture de i est connue a la decision).
- Entree (etat neutre) : cible 1 si SMA_rapide[i-1] <= SMA_lente[i-1] et SMA_rapide[i] > SMA_lente[i] (croisement strict a la hausse).
- Sortie (etat long) : cible 0 si SMA_rapide[i-1] >= SMA_lente[i-1] et SMA_rapide[i] < SMA_lente[i] (croisement strict a la baisse).
- Sinon l'etat ne change pas : la cible reste celle de l'etat courant.
- Au debut de chaque periode l'etat repart a neutre (SPEC) : si la rapide est deja au-dessus de la lente, on reste neutre jusqu'au prochain croisement.
- Les WARMUP premieres bougies : cible 0.
- Pas de short, pas de levier, pas de filtre, pas de stop.

## Parametres
Une journee = 6 bougies 4h.

| nom | role | valeurs possibles |
|-----|------|-------------------|
| F | bougies de la SMA rapide (5, 10 ou 15 jours) | 30, 60, 90 |
| S | bougies de la SMA lente (20, 30 ou 40 jours) | 120, 180, 240 |

## WARMUP
WARMUP = S, car il faut la SMA lente aux index i-1 et i.

## Combinaisons a tester sur le train (9)
1. F=30, S=120
2. F=30, S=180
3. F=30, S=240
4. F=60, S=120
5. F=60, S=180
6. F=60, S=240
7. F=90, S=120
8. F=90, S=180
9. F=90, S=240

## Regle de choix
Les voisines d'une combinaison sont celles qui different d'un seul cran en F ou en S dans la grille (pas en diagonale). On retient une combinaison qui passe les 4 criteres ET dont toutes les voisines passent aussi les 4 criteres. S'il y en a plusieurs, on prend celle au capital final le plus eleve parmi elles. S'il n'y en a aucune, l'idee est abandonnee. Cette regle est fixee avant tout resultat et ne change pas.

## Ce qui prouverait que l'idee est fausse
Aucune combinaison ne satisfait la regle de choix : soit aucune ne passe les 4 criteres, soit les combinaisons qui passent sont isolees, soit il y a moins de 30 trades partout. L'idee est alors abandonnee, sans nouvelle combinaison ni filtre ajoute. Un echec au train ne compte pas dans la condition d'arret. Regle supplementaire posee avant tout resultat : si cette idee echoue au train, on n'essaie plus de strategie de tendance ; les variantes vont au BACKLOG.

## Estimation du nombre de trades (par raisonnement, avant tout resultat)
Estimation de l'auteur : 35 a 50 trades sur 156 semaines (1 trade = 1 croisement haussier + le croisement baissier suivant). Cette estimation n'est pas demontree : elle suppose un croisement toutes les 2 semaines sans relier cette frequence aux fenetres. Le risque que c1 echoue est accepte, c'est le train qui mesure.

## Transparence
- Le texte initial de la strategie (EMA, ATR, stop, short) a ete propose par une autre IA ayant probablement vu des prix 2024-2026. Il a ete refuse (short, sizing ATR, filtres hors perimetre) ; seule l'idee de croisement de moyennes simples est retenue.
- Meme hypothese que donchian (persistance des tendances).
- La grille 3x3 est un elagage d'une liste de 11 combinaisons, decide apres avoir vu le tableau de resultats train de donchian : les valeurs ne sont donc pas prouvees choisies a froid.
- Si le test passe, la preuve est plus faible qu'une idee nee a froid.
