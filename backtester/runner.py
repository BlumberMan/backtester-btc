import argparse
import ast
import importlib.util
import sys
from pathlib import Path

from backtester import gate
from backtester.data import load_train
from backtester.lock import LockError, append_result, check_lock, validate_name

# Pas d'import de backtester.holdout ici : il est importe dans run_test seulement. Ainsi, la
# commande train ne charge meme pas le module capable de lire le test (SPEC, "Seule la commande
# de test charge le test").

DATA_PATH = "data/BTCUSDT_4h.csv"
RESULTS_PATH = "docs/resultats_test.md"
STRATEGIES_DIR = "backtester/strategies"

# Appels interdits dans une strategie : open lit des fichiers (donc potentiellement le CSV et le
# test), eval/exec/__import__ executeraient ou importeraient du code que l'analyse ast ne voit pas.
FORBIDDEN_CALLS = {"open", "eval", "exec", "__import__"}


def strategy_path(name, strategies_dir):
    """Retourne Path(strategies_dir) / "<name>.py".

    validate_name d'abord : le nom vient de la ligne de commande et sert a construire un chemin.
    Sans ce controle, "../x" ou un nom absolu ferait charger un fichier hors du dossier des
    strategies, et ce nom ne pourrait de toute facon pas etre celui d'un tag test-<nom>.
    """
    validate_name(name)
    return Path(strategies_dir) / f"{name}.py"


def _check_source(tree, path):
    """Leve ValueError si l'ast de la strategie viole les regles de la SPEC (Interface strategie).

    - import hors stdlib : une dependance externe pourrait changer de version et donc changer les
      cibles sans que le fichier gele par le tag ne change. On teste le premier segment
      ("os.path" -> "os") contre sys.stdlib_module_names, la liste officielle de l'interpreteur.
    - import relatif (from . import x) : il viserait un module du projet, jamais la stdlib.
    - import commencant par "backtester" : la strategie pourrait appeler data, holdout ou engine,
      donc lire le test ou recalculer le buy and hold hors de la commande de test.
    - appel a open, eval, exec ou __import__ : lecture de fichier ou code dynamique invisible ici.

    C'est un garde-fou contre les erreurs, pas un bac a sable : un code ecrit pour contourner
    l'analyse (getattr(builtins, "open"), etc.) passerait. Le but est qu'un oubli soit refuse
    bruyamment, pas de resister a une strategie malveillante, que j'ecris moi-meme.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:
                raise ValueError(f"{path} : import relatif interdit (stdlib uniquement)")
            modules = [node.module]
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
            raise ValueError(f"{path} ligne {node.lineno} : appel a {node.func.id} interdit")
        else:
            continue
        for module in modules:
            if module.startswith("backtester"):
                raise ValueError(f"{path} : import de {module} interdit (aucun import de backtester)")
            if module.split(".")[0] not in sys.stdlib_module_names:
                raise ValueError(f"{path} : import de {module} interdit (stdlib uniquement)")


def load_strategy(path):
    """Charge le fichier strategie par son chemin et retourne le module.

    Par le chemin et non par "import backtester.strategies.x" : le nom de tag peut contenir "-"
    (ema-50), qui n'est pas un identifiant Python valide. Le nom de module interne remplace donc
    "-" par "_" ; il n'est pas ajoute a sys.modules, rien d'autre ne doit pouvoir l'importer.

    Le source est lu une seule fois, analyse avec ast, puis c'est CE MEME arbre qui est compile
    et execute : le code verifie est exactement le code execute (pas de relecture du fichier entre
    les deux), et aucun __pycache__ n'est ecrit a cote de la strategie, ce qui salirait l'arbre git
    et ferait refuser le run test par le verrou.

    Apres execution, WARMUP doit etre un int >= 0 (bool refuse : True vaut 1 mais signale une
    erreur de saisie, pas un historique voulu) et compute_targets doit etre appelable. Sans ces
    controles, une strategie mal ecrite planterait plus loin, apres le verrou, en plein run test.
    """
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"strategie introuvable : {path}")
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as e:
        raise ValueError(f"{path} : erreur de syntaxe ligne {e.lineno}") from e
    _check_source(tree, path)

    module_name = "strategy_" + path.stem.replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(tree, str(path), "exec"), module.__dict__)

    warmup = getattr(module, "WARMUP", None)
    if type(warmup) is not int or warmup < 0:
        raise ValueError(f"{path} : WARMUP doit etre un entier >= 0, trouve {warmup!r}")
    if not callable(getattr(module, "compute_targets", None)):
        raise ValueError(f"{path} : compute_targets absent ou non appelable")
    return module


def period_targets(strategy, history, period):
    """Retourne les cibles de la periode seule (meme longueur que period).

    compute_targets recoit history + period : la strategie voit l'historique pour calculer ses
    indicateurs des la premiere bougie de la periode. Chaque cible doit etre exactement l'int 0
    ou 1 (type(t) is int) : True ou 1.0 passeraient "t in (0, 1)" mais revelent un bug dans la
    strategie, et le resultat du test est definitif, on refuse plutot que d'interpreter.

    Les len(history) premieres cibles sont retirees : elles portent sur des bougies hors periode,
    le moteur ne les simule pas. Puis les max(0, WARMUP - len(history)) premieres cibles restantes
    sont forcees a 0 : si l'historique ne couvre pas tout le WARMUP (train, qui n'a aucune bougie
    avant 2021-01-01), les indicateurs sont incomplets sur ces bougies-la. Avec un historique
    suffisant (test), rien n'est force.

    Pourquoi ici et pas dans la strategie (SPEC, Interface strategie) : la strategie ne sait pas
    ou commence la periode, elle ne voit qu'une liste de bougies. Si chaque strategie faisait son
    propre forcage, un oubli ou une erreur d'un indice ouvrirait des trades sur des indicateurs
    faux, et chaque strategie devrait etre verifiee a part. Fait une seule fois ici, la regle est
    la meme pour toutes et testee une fois.
    """
    targets = strategy.compute_targets(history + period)
    if not isinstance(targets, list) or len(targets) != len(history) + len(period):
        raise ValueError(f"compute_targets doit retourner une liste de {len(history) + len(period)} cibles")
    for i, t in enumerate(targets):
        if type(t) is not int or t not in (0, 1):
            raise ValueError(f"cible {i} invalide : {t!r} (int 0 ou 1 attendu)")

    targets = targets[len(history):]
    n_forced = max(0, strategy.WARMUP - len(history))
    return [0] * min(n_forced, len(targets)) + targets[n_forced:]


def run_train(name, data_path, strategies_dir):
    """Lance le gate P3 sur le train et retourne {"warmup": WARMUP, **resultat de gate.evaluate}.

    history vide : le dataset commence au 2021-01-01, il n'y a aucune bougie avant, donc les
    WARMUP premieres cibles du train sont forcees a 0 par period_targets. Aucune fonction ici ne
    peut lire le test : load_train s'arrete avant 2024-01-01, et holdout n'est pas importe.
    """
    candles = load_train(data_path)
    strategy = load_strategy(strategy_path(name, strategies_dir))
    targets = period_targets(strategy, [], candles)
    return {"warmup": strategy.WARMUP, **gate.evaluate(candles, targets)}


def run_test(name, data_path, strategies_dir, repo_dir, results_path):
    """Lance l'unique run test de name et retourne le resultat, deja ecrit dans results_path.

    L'ordre est la regle (SPEC, Gate P3 etapes 4 a 6, Verrou renforce, Plantage du run test) :
    1. check_lock en premier : si le verrou refuse, le test n'est jamais lu, pas meme charge.
    2. load_strategy avant load_test : une strategie invalide est refusee avant de lire le test,
       et on a besoin de son WARMUP pour savoir combien de bougies du train fournir.
    3. holdout importe seulement ici, apres le verrou : c'est le seul chemin qui charge le test.
    4. period_targets avec les bougies de warmup comme historique, gate.evaluate sur le test.
    5. append_result AVANT tout affichage : aucun print ici. Si un chiffre etait affiche puis que
       l'ecriture plantait, le run serait consomme sans trace et le verrou ne bloquerait pas un
       second run. L'affichage est fait par main, une fois le resultat sur le disque.
    """
    check_lock(name, repo_dir, results_path)
    strategy = load_strategy(strategy_path(name, strategies_dir))
    from backtester.holdout import load_test

    warmup_candles, test_candles = load_test(data_path, strategy.WARMUP)
    targets = period_targets(strategy, warmup_candles, test_candles)
    result = {"warmup": strategy.WARMUP, **gate.evaluate(test_candles, targets)}
    append_result(name, result, results_path)
    return result


def _print_result(result):
    for key, value in result.items():
        print(f"{key}: {value}")


def main(argv=None):
    """Point d'entree : "train <nom>" ou "test <nom>".

    Deux sous-commandes distinctes pour que le test ne puisse jamais etre lance par erreur avec
    le train : il faut taper "test" explicitement. LockError et ValueError sont des refus attendus
    (verrou, strategie ou donnees invalides) : une ligne sur stderr et le code 1, sans traceback,
    pour les distinguer d'un vrai plantage. Le message tient sur une ligne meme quand le verrou
    liste les fichiers modifies.
    """
    parser = argparse.ArgumentParser(prog="python -m backtester.runner")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("train", help="gate P3 sur le train (2021-2023)").add_argument("name")
    sub.add_parser("test", help="unique run test (2024-2026), verrouille").add_argument("name")
    args = parser.parse_args(argv)

    try:
        if args.command == "train":
            _print_result(run_train(args.name, DATA_PATH, STRATEGIES_DIR))
        else:
            result = run_test(args.name, DATA_PATH, STRATEGIES_DIR, Path.cwd(), RESULTS_PATH)
            _print_result(result)
            print(f"Resultat ecrit dans {RESULTS_PATH} : commite-le MAINTENANT (git add {RESULTS_PATH}, git commit)")
    except (LockError, ValueError) as e:
        message = " ; ".join(line for line in str(e).splitlines() if line.strip())
        print(f"erreur : {message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
