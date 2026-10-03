"""Balayage de la grille donchian sur le train et application de la regle de choix.

Grille et regle de choix : docs/strategies/donchian.md (Gate P3, etape 2). Rien n'est ecrit dans un
fichier : le choix est recopie a la main dans docs/strategies/donchian.md, comme l'exige l'etape 2.
"""

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

from backtester import gate
from backtester.data import load_train
from backtester.runner import (
    DATA_PATH, DATA_SHA256, STRATEGIES_DIR, check_causality, check_data_hash, load_strategy,
    period_targets, strategy_path,
)

# Aucun import de backtester.holdout, meme dans une fonction : le balayage est une optimisation,
# il ne doit jamais pouvoir lire le test (SPEC, Gate P3 etape 2 : seules les combinaisons listees,
# sur le train). load_train s'arrete avant 2024-01-01, c'est la seule lecture de donnees ici.

# Valeurs de docs/strategies/donchian.md, copiees telles quelles et dans le meme ordre : la grille
# est fixee avant tout resultat, la modifier ici serait tester une combinaison non listee.
GRID_N = (60, 120, 240)
GRID_M = (30, 60, 120)
# N en boucle externe, M en boucle interne : c'est l'ordre de la liste numerotee du .md (1 a 9),
# donc la ligne k du tableau affiche correspond a la combinaison k du document.
GRID = [(n, m) for n in GRID_N for m in GRID_M]


class ChoiceRuleError(ValueError):
    """Cas que la regle de choix ecrite dans donchian.md ne tranche pas.

    Sous-classe de ValueError pour que main le traite comme un refus attendu (une ligne, code 1).
    Classe a part pour qu'un test puisse distinguer ce refus d'une autre ValueError : la regle
    est fixee avant tout resultat, on ne l'invente pas apres coup, on s'arrete et je decide.
    """


def make_strategy(targets_fn, n, m):
    """Retourne un objet strategie (WARMUP, compute_targets) pour la combinaison (n, m).

    SimpleNamespace plutot qu'un fichier par combinaison : runner.check_causality et
    runner.period_targets n'ont besoin que de ces deux attributs, et la logique reste celle de
    donchian_targets, la fonction meme qui sera gelee par le tag. WARMUP = max(n, m) comme dans
    donchian.md (section WARMUP).

    n=n, m=m en arguments par defaut : un lambda lit ses variables libres au moment de l'appel, pas
    a sa creation. Sans ce figeage, un objet cree dans une boucle pourrait calculer avec le (n, m)
    d'une iteration suivante.
    """
    return SimpleNamespace(WARMUP=max(n, m), compute_targets=lambda c, n=n, m=m: targets_fn(c, n, m))


def sweep(candles, grid, targets_fn):
    """Retourne une liste de dicts {n, m, **gate.evaluate}, un par combinaison, dans l'ordre de grid.

    targets_fn = donchian_targets, passe par l'appelant : main la recupere via runner.load_strategy,
    donc le code balaye est celui qui passe les controles d'import du runner, et les tests peuvent
    fournir des bougies synthetiques sans toucher a data/.

    Pour chaque combinaison, le meme chemin que runner.run_train : WARMUP > len(candles) refuse
    (tout serait force a 0, 0 trade sans explication), check_causality, period_targets avec un
    historique vide (le train n'a aucune bougie avant 2021-01-01), puis gate.evaluate. Les memes
    fonctions, pas une copie : le balayage juge exactement ce que run_train jugera.
    """
    results = []
    for n, m in grid:
        strategy = make_strategy(targets_fn, n, m)
        if strategy.WARMUP > len(candles):
            raise ValueError(f"WARMUP ({strategy.WARMUP}) depasse le train ({len(candles)} bougies) pour N={n}, M={m}")
        check_causality(strategy, candles)
        targets = period_targets(strategy, [], candles)
        results.append({"n": n, "m": m, **gate.evaluate(candles, targets)})
    return results


def neighbors(grid_n, grid_m, n, m):
    """Retourne les combinaisons a un seul cran de (n, m) en N ou en M, dans l'ordre de la grille.

    Un cran = indice voisin dans grid_n ou grid_m, pas une distance en valeur : 60 -> 120 -> 240 est
    une grille geometrique, seul l'indice a un sens. Distance d'indices |di| + |dj| == 1 : exclut la
    combinaison elle-meme (0) et les diagonales (2), comme le dit donchian.md.
    """
    i, j = grid_n.index(n), grid_m.index(m)
    return [
        (grid_n[a], grid_m[b])
        for a in range(len(grid_n))
        for b in range(len(grid_m))
        if abs(a - i) + abs(b - j) == 1
    ]


def choose(results):
    """Applique la regle de choix de donchian.md et retourne le dict retenu, ou None.

    Regle : candidate = passe les 4 criteres ET toutes ses voisines aussi. Plusieurs candidates :
    celle au final_normal le plus eleve. Aucune : None (idee abandonnee). Exiger les voisines
    ecarte un pic isole, qui a plus de chances d'etre du bruit que d'un avantage reel.

    Fonction pure : ne lit que results. ChoiceRuleError si results ne couvre pas exactement GRID
    (une voisine absente ne peut pas etre jugee, la regle suppose la grille complete), ou si
    plusieurs candidates sont a egalite exacte sur le meilleur final_normal (la regle ne dit pas
    laquelle prendre, et choisir apres avoir vu les chiffres est justement ce qu'elle interdit).
    """
    by_combo = {(r["n"], r["m"]): r for r in results}
    if len(results) != len(GRID) or set(by_combo) != set(GRID):
        raise ChoiceRuleError(f"les resultats doivent couvrir exactement les {len(GRID)} combinaisons de la grille")

    candidates = [
        r for r in results
        if r["passed"] and all(by_combo[v]["passed"] for v in neighbors(GRID_N, GRID_M, r["n"], r["m"]))
    ]
    if not candidates:
        return None
    best = max(r["final_normal"] for r in candidates)
    top = [r for r in candidates if r["final_normal"] == best]
    if len(top) > 1:
        combos = ", ".join(f"N={r['n']} M={r['m']}" for r in top)
        raise ChoiceRuleError(f"egalite exacte de final_normal ({best}) entre {combos} : cas non couvert par la regle")
    return top[0]


def _print_table(results):
    # Montants a 2 decimales : le gate P2 compare a 0,01 USDT pres, plus de precision n'apporte rien.
    print(f"{'n':>4} {'m':>4} {'n_trades':>8} {'final_normal':>13} {'final_doubled':>13} {'final_bh':>13}"
          f" {'c1':>5} {'c2':>5} {'c3':>5} {'c4':>5} {'passed':>6}")
    for r in results:
        print(f"{r['n']:>4} {r['m']:>4} {r['n_trades']:>8} {r['final_normal']:>13.2f} {r['final_doubled']:>13.2f}"
              f" {r['final_bh']:>13.2f} {r['c1']!s:>5} {r['c2']!s:>5} {r['c3']!s:>5} {r['c4']!s:>5} {r['passed']!s:>6}")


def main(argv=None):
    """Point d'entree : python -m backtester.sweep, sans argument.

    argparse sans argument : un argument en trop (un nom de strategie, "test"...) est refuse au
    lieu d'etre ignore en silence. Meme ordre que run_train : fichier present, hash verifie avant de
    lire une bougie (le choix doit porter sur les donnees verifiees en P1), puis load_train.

    donchian_targets est recuperee par runner.load_strategy et non par un import : c'est le meme
    chargement que pour le run train et le run test, avec les memes controles d'imports.

    ValueError (donc ChoiceRuleError) : refus attendu, une ligne sur stderr et code 1, comme
    runner.main. Le tableau est affiche avant le verdict : en cas d'egalite, les 9 lignes restent
    visibles pour que je tranche a la main.
    """
    parser = argparse.ArgumentParser(prog="python -m backtester.sweep")
    parser.parse_args(argv)

    try:
        if not Path(DATA_PATH).is_file():
            raise ValueError(f"donnees introuvables : {DATA_PATH}")
        check_data_hash(DATA_PATH, DATA_SHA256)
        candles = load_train(DATA_PATH)
        strategy = load_strategy(strategy_path("donchian", STRATEGIES_DIR))
        if not callable(getattr(strategy, "donchian_targets", None)):
            raise ValueError("donchian_targets absent ou non appelable dans la strategie donchian")
        results = sweep(candles, GRID, strategy.donchian_targets)
        _print_table(results)
        chosen = choose(results)
        if chosen is None:
            print("AUCUNE : idee abandonnee")
        else:
            print(f"RETENUE : N={chosen['n']}, M={chosen['m']} (final_normal {chosen['final_normal']:.2f})")
    except ValueError as e:
        message = " ; ".join(line for line in str(e).splitlines() if line.strip())
        print(f"erreur : {message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
