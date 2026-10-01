# SPEC - backtester-btc

## Objectif
Construire un backtester de A a Z dont je comprends et maitrise absolument chaque ligne de code. La rentabilite financiere est un bonus ; le succes se mesure a la creation d'un outil formateur, fiable et presentable pour mes futurs stages ou mon CV.

## Perimetre
Creation d'un environnement de backtest automatise en Python 3.14 pour le trading algorithmique, centre sur la paire BTC/USDT. Decisions techniques : spot Binance uniquement (pas de futures), timeframe 4h, horodatage UTC. Cela inclut l'ingestion de donnees propres (Binance API), un moteur de simulation integrant les frais et le slippage, un systeme de validation rigoureux et un module de paper trading.

## Interdits
- Pas de Machine Learning avant d'avoir valide le palier P3.
- Pas d'utilisation d'effet de levier.
- Un seul actif (BTC/USDT).
- Une seule timeframe (4h).
- Modifier ou ajuster les parametres d'une strategie apres avoir vu les resultats de la periode de test.
- Passer au palier suivant sans avoir valide la "Gate" precedente avec des preuves tangibles (logs, diffs, calculs manuels).
- Coder aveuglement en copiant les sorties de l'agent IA sans en comprendre la logique.

## Periodes
- **In-sample (Entrainement / Optimisation) :** 2021-01-01 au 2023-12-31 inclus, en UTC.
- **Out-of-sample (Test) :** 2024-01-01 au 2026-08-31 inclus, en UTC (cette periode ne doit etre regardee qu'une seule fois par strategie).

## Gate P3
- **Periodes :** train = open_time dans [2021-01-01 00:00, 2024-01-01 00:00[ UTC ; test = open_time dans [2024-01-01 00:00, 2026-09-01 00:00[ UTC (memes periodes que la section "Periodes", ecrites comme dans le code).
- **Prechauffage :** une strategie peut lire les bougies anterieures au debut de la periode pour calculer ses indicateurs. Ses cibles valent 0 pour toute bougie anterieure au debut de la periode : aucun trade ne s'ouvre avant le 2e open de la periode.
- **Buy and hold de reference :** run_backtest sur les bougies de la periode avec toutes les cibles a 1, memes frais et slippage.
- **Critere 1 :** au moins 30 trades.
- **Critere 2 :** capital final > 1000 USDT avec f = 0.001 et s = 0.0005.
- **Critere 3 :** capital final >= 1000 USDT avec f = 0.002 et s = 0.001.
- **Critere 4 :** capital final > capital final du buy and hold de reference (f = 0.001, s = 0.0005).
- **Application :** les 4 criteres s'appliquent d'abord au train, puis au test.
- **Etape 1 - Ecriture :** avant tout code, l'idee est ecrite dans docs/strategies/<nom>.md : regles d'entree et de sortie, parametres, et liste des combinaisons de parametres a tester sur le train (20 maximum).
- **Etape 2 - Train :** seules les combinaisons listees sont testees. Une seule est retenue, et ce choix est ecrit dans le meme fichier.
- **Etape 3 - Echec au train :** idee abandonnee. Cet echec ne compte pas dans la condition d'arret.
- **Etape 4 - Gel :** la strategie et ses parametres sont commites, puis un tag git test-<nom> est pose avant le run test.
- **Etape 5 - Test :** un seul run, par une commande dediee. Le resultat est ajoute a docs/resultats_test.md et commite immediatement, y compris en cas d'echec.
- **Etape 6 - Verrou :** la commande de test refuse de s'executer si <nom> figure deja dans docs/resultats_test.md.
- **Etape 7 - Echec au test :** idee abandonnee definitivement. Aucune variante de la meme regle (autres parametres, filtre ajoute) ne peut etre retestee.
- **Anti-lookahead :** chaque strategie a un test obligatoire : modifier les bougies posterieures a t ne change aucune cible jusqu'a t.

Tout echec ou resultat neutre entraine l'abandon immediat de l'idee, sans aucune tentative de reajustement.

## Regles complementaires P3
- **Prechauffage sur le train :** le dataset commence au 2021-01-01, il n'y a aucune bougie avant. Chaque strategie declare sa fenetre WARMUP (nombre de bougies d'historique necessaires). Sur le train, ses cibles valent 0 pour les WARMUP premieres bougies. Sur le test, elle peut lire les bougies du train qui precedent le 2024-01-01, avec des cibles a 0 avant le debut du test.
- **Chargement des donnees :** la fonction de chargement du train ne retourne jamais de bougie avec open_time >= 2024-01-01. Seule la commande de test charge le test.
- **Verrou renforce :** la commande de test refuse de s'executer si le tag test-<nom> n'existe pas, si HEAD n'est pas ce tag, si l'arbre git n'est pas propre, ou si <nom> figure deja dans docs/resultats_test.md.
- **Plantage du run test :** le resultat est ecrit dans docs/resultats_test.md avant tout affichage. Si la commande plante avant cette ecriture, aucun chiffre n'a ete vu : un bug d'infrastructure peut etre corrige sur un nouveau commit, puis le tag test-<nom> est deplace dessus (git tag -f test-<nom>), uniquement si git diff entre l'ancien et le nouveau commit ne touche aucun fichier de backtester/strategies/ ni de docs/strategies/. Le nom de la strategie ne change jamais. Si un chiffre a ete vu, le run est consomme.
- **Buy and hold du test :** calcule uniquement par la commande de test. Interdit de calculer, tracer ou regarder le prix ou le buy and hold de 2024-2026 en dehors de cette commande.
- **Demarrage de chaque periode :** la strategie ne recoit que WARMUP bougies d'historique, donc son etat interne (long ou neutre) repart de zero au debut du train comme du test, meme si elle aurait ete en position a la fin de la periode precedente. Le buy and hold achete des le 2e open de la periode : c'est un handicap connu pour le critere 4, accepte a l'avance.

## Interface strategie
- Une strategie est un fichier backtester/strategies/<nom>.py, ou <nom> est celui du tag test-<nom>. Le fichier est charge par son chemin, donc "-" est autorise dans le nom.
- Elle definit une constante entiere WARMUP (>= 0) et une fonction compute_targets(candles) -> list[int] de 0 ou 1, de meme longueur que candles. candles = tuples du moteur (open_time, open, high, low, close).
- La cible a l'index i ne depend que de candles[0..i] (test anti-lookahead obligatoire).
- Stdlib uniquement. Aucune lecture de fichier, aucune date en dur, aucun import de data, lock, gate ou engine. Les parametres sont des constantes du fichier.
- Le forcage des cibles a 0 pendant le prechauffage est fait par l'appelant, jamais par la strategie.

## Condition d'arret
- Trois idees de strategie echouees au test (etape 7 du gate P3) : fin du volet trading, le projet s'arrete la et le backtester reste uniquement comme projet personnel. Les echecs au train ne comptent pas.

## Moteur (P2)
- Spot, long ou neutre uniquement : position 0 (100 % USDT) ou 1 (100 % BTC). Pas de short : sur spot, shorter impose d'emprunter, donc du levier (interdit).
- Entree du moteur : les bougies propres + une position cible (0 ou 1) par bougie, decidee a la cloture de cette bougie. Le moteur ne contient aucune strategie.
- Execution : une cible decidee a la cloture de la bougie t s'execute a l'open de la bougie t+1. La cible de la derniere bougie est ignoree. Cible identique a la position actuelle : rien ne se passe.
- Slippage : s = 0,05 % defavorable. Achat a open x (1 + s), vente a open x (1 - s).
- Frais : f = 0,1 % du montant echange, a chaque achat et a chaque vente (taux spot Binance standard, sans reduction BNB).
- Achat : qty_btc = cash x (1 - f) / prix_achat, puis cash = 0.
- Vente : cash = qty_btc x prix_vente x (1 - f), puis qty_btc = 0.
- Capital initial : 1000 USDT. Fractions de BTC sans arrondi (simplification connue : pas de pas de lot ni de montant minimum Binance).
- Fin des donnees : une position ouverte est fermee au close de la derniere bougie, avec slippage et frais.
- Un trade = une entree + la sortie correspondante.
- Sorties : capital final en USDT, nombre de trades, liste des trades (date et prix d'entree, date et prix de sortie, resultat net en USDT).
- f et s sont des parametres (le gate P3 les double).
- Calculs en float ; le gate P2 compare au calcul a la main a 0,01 USDT pres.

## Paliers
- **P0 - Infra :** Repo Git, SPEC.md, requirements.txt. 
  *Gate :* Clonage et lancement fonctionnels sur une machine vierge.
- **P1 - Donnees :** Script de telechargement des bougies avec gestion des trous, doublons et fuseaux horaires. 
  *Gate :* 2 executions successives donnent un dataset 100% identique.
- **P2 - Moteur de backtest :** Simulation des trades incluant frais et slippage. 
  *Gate :* Le resultat calcule par le moteur sur 10 bougies est identique au calcul fait a la main sur papier.
- **P3 - Validation :** Train sur 2021-2023, Test sur 2024-2026. 
  *Gate :* voir section "Gate P3" ci-dessus (4 criteres, train puis test).
- **P4 - Paper trading :** Live sans argent reel pendant 2 mois minimum. 
  *Gate :* critere chiffre fixe avant le demarrage de P4, jamais pendant.
- **P5 - Argent reel :** 100 € maximum alloues pour tester la psychologie face au marche reel.