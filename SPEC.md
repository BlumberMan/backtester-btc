# SPEC - backtester-btc

## Objectif

Construire un backtester de A a Z dont je comprends et maitrise absolument chaque ligne de code. La rentabilite financiere est un bonus ; le succes se mesure a la creation d'un outil formateur, fiable et presentable pour mes futurs stages ou mon CV.

## Perimetre

Creation d'un environnement de backtest automatise en Python 3.14 pour le trading algorithmique, centre sur la paire BTC/USDT. Decisions techniques : spot Binance uniquement (pas de futures), timeframe 4h, horodatage UTC. Cela inclut l'ingestion de donnees propres (Binance API), un moteur de simulation integrant les frais et le slippage, un systeme de validation rigoureux et un module de paper trading.

## Interdits

* Pas de Machine Learning avant d'avoir valide le palier P3.
* Pas d'utilisation d'effet de levier.
* Un seul actif (BTC/USDT).
* Une seule timeframe (4h).
* Modifier ou ajuster les parametres d'une strategie apres avoir vu les resultats de la periode de test.
* Passer au palier suivant sans avoir valide la "Gate" precedente avec des preuves tangibles (logs, diffs, calculs manuels).
* Coder aveuglement en copiant les sorties de l'agent IA sans en comprendre la logique.

## Periodes

* **In-sample (Entrainement / Optimisation) :** 2021-01-01 au 2023-12-31 inclus, en UTC.
* **Out-of-sample (Test) :** 2024-01-01 au 2026-08-31 inclus, en UTC (cette periode ne doit etre regardee qu'une seule fois par strategie).

## Gate P3

La strategie doit respecter les criteres suivants sur la periode de test out-of-sample :

* Au moins 30 trades effectues sur la periode.
* Un resultat net positif apres frais et slippage.
* Un resultat toujours superieur ou egal a 0 avec des frais et un slippage doubles.

Tout echec ou resultat neutre entraine l'abandon immediat de l'idee, sans aucune tentative de reajustement.

## Condition d'arret

* Trois idees de strategie echouees au gate P3 : fin du volet trading, le projet s'arrete la et le backtester reste uniquement comme projet personnel.

## Moteur 

\## Moteur (P2)

\- Spot, long ou neutre uniquement : position 0 (100 % USDT) ou 1 (100 % BTC). Pas de short : sur spot, shorter impose d'emprunter, donc du levier (interdit).

\- Entree du moteur : les bougies propres + une position cible (0 ou 1) par bougie, decidee a la cloture de cette bougie. Le moteur ne contient aucune strategie.

\- Execution : une cible decidee a la cloture de la bougie t s'execute a l'open de la bougie t+1. La cible de la derniere bougie est ignoree. Cible identique a la position actuelle : rien ne se passe.

\- Slippage : s = 0,05 % defavorable. Achat a open x (1 + s), vente a open x (1 - s).

\- Frais : f = 0,1 % du montant echange, a chaque achat et a chaque vente (taux spot Binance standard, sans reduction BNB).

\- Achat : qty\_btc = cash x (1 - f) / prix\_achat, puis cash = 0.

\- Vente : cash = qty\_btc x prix\_vente x (1 - f), puis qty\_btc = 0.

\- Capital initial : 1000 USDT. Fractions de BTC sans arrondi (simplification connue : pas de pas de lot ni de montant minimum Binance).

\- Fin des donnees : une position ouverte est fermee au close de la derniere bougie, avec slippage et frais.

\- Un trade = une entree + la sortie correspondante.

\- Sorties : capital final en USDT, nombre de trades, liste des trades (date et prix d'entree, date et prix de sortie, resultat net en USDT).

\- f et s sont des parametres (le gate P3 les double).

\- Calculs en float ; le gate P2 compare au calcul a la main a 0,01 USDT pres.

## Paliers

* **P0 - Infra :** Repo Git, SPEC.md, requirements.txt.
*Gate :* Clonage et lancement fonctionnels sur une machine vierge.
* **P1 - Donnees :** Script de telechargement des bougies avec gestion des trous, doublons et fuseaux horaires.
*Gate :* 2 executions successives donnent un dataset 100% identique.
* **P2 - Moteur de backtest :** Simulation des trades incluant frais et slippage.
*Gate :* Le resultat calcule par le moteur sur 10 bougies est identique au calcul fait a la main sur papier.
* **P3 - Validation :** Train sur 2021-2023, Test sur 2024-2026.
*Gate :* voir section "Gate P3" ci-dessus (3 criteres).
* **P4 - Paper trading :** Live sans argent reel pendant 2 mois minimum.
*Gate :* critere chiffre fixe avant le demarrage de P4, jamais pendant.
* **P5 - Argent reel :** 100 € maximum alloues pour tester la psychologie face au marche reel.





