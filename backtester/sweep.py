"""Balayage de la grille d'une strategie sur le train et application de la regle de choix.

Grilles et regle de choix : docs/strategies/<nom>.md (Gate P3, etape 2). Rien n'est ecrit dans un
fichier : le choix est recopie a la main dans docs/strategies/<nom>.md, comme l'exige l'etape 2.
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

# Une entree par strategie balayable. La cle est le nom du fichier backtester/strategies/<nom>.py
# (et du .md), pour que la ligne de commande, le chargement et la doc designent la meme chose.
# "targets" : nom de la fonction parametree du module, recuperee par getattr apres load_strategy.
# "names" : noms des deux parametres en minuscules, cles des resultats et en-tete du tableau.
# "grids" : valeurs de docs/strategies/<nom>.md, copiees telles quelles et dans le meme ordre : la
# grille est fixee avant tout resultat, la modifier ici serait tester une combinaison non listee.
STRATEGIES = {
    "donchian": {
        "targets": "donchian_targets",
        "names": ("n", "m"),
        "grids": ((60, 120, 240), (30, 60, 120)),
    },
    "sma-cross": {
        "targets": "sma_cross_targets",
        "names": ("f", "s"),
        "grids": ((30, 60, 90), (120, 180, 240)),
    },
}


def product_grid(grid_a, grid_b):
    """Retourne les combinaisons (a, b), grid_a en boucle externe et grid_b en boucle interne.

    C'est l'ordre des listes numerotees des .md (1 a 9), donc la ligne k du tableau affiche
    correspond a la combinaison k du document.
    """
    return [(a, b) for a in grid_a for b in grid_b]


# Noms historiques de la grille donchian, gardes pour que les appels et tests existants ne changent
# pas : ce sont aussi les valeurs par defaut de choose, donc sans argument le comportement reste
# exactement celui de donchian.
GRID_N, GRID_M = STRATEGIES["donchian"]["grids"]
GRID = product_grid(GRID_N, GRID_M)


class ChoiceRuleError(ValueError):
    """Cas que la regle de choix ecrite dans les .md ne tranche pas.

    Sous-classe de ValueError pour que main le traite comme un refus attendu (une ligne, code 1).
    Classe a part pour qu'un test puisse distinguer ce refus d'une autre ValueError : la regle
    est fixee avant tout resultat, on ne l'invente pas apres coup, on s'arrete et je decide.
    """


def _label(names, a, b, sep=" "):
    # Noms en majuscules dans les messages, comme dans les .md (N, M, F, S) : "N=120 M=60".
    return f"{names[0].upper()}={a}{sep}{names[1].upper()}={b}"


def make_strategy(targets_fn, a, b):
    """Retourne un objet strategie (WARMUP, compute_targets) pour la combinaison (a, b).

    SimpleNamespace plutot qu'un fichier par combinaison : runner.check_causality et
    runner.period_targets n'ont besoin que de ces deux attributs, et la logique reste celle de
    targets_fn, la fonction meme qui sera gelee par le tag.

    WARMUP = max(a, b) :
    - donchian : max(N, M), comme dans donchian.md (section WARMUP) ;
    - sma-cross : sma-cross.md ecrit WARMUP = S. Dans la grille, S (120 a 240) est toujours
      strictement superieur a F (30 a 90), donc max(F, S) = S : meme valeur, sans cas particulier.
      Un test verifie S > F sur toute la grille, pour que cette egalite ne casse pas en silence si
      la grille changeait.

    a=a, b=b en arguments par defaut : un lambda lit ses variables libres au moment de l'appel, pas
    a sa creation. Sans ce figeage, un objet cree dans une boucle pourrait calculer avec le (a, b)
    d'une iteration suivante.
    """
    return SimpleNamespace(WARMUP=max(a, b), compute_targets=lambda c, a=a, b=b: targets_fn(c, a, b))


def sweep(candles, grid, targets_fn, names=("n", "m")):
    """Retourne une liste de dicts {names[0], names[1], **gate.evaluate}, un par combinaison, dans
    l'ordre de grid. names vaut ("n", "m") par defaut : les cles donchian d'origine.

    targets_fn (donchian_targets, sma_cross_targets) est passee par l'appelant : main la recupere
    via runner.load_strategy, donc le code balaye est celui qui passe les controles d'import du
    runner, et les tests peuvent fournir des bougies synthetiques sans toucher a data/.

    Pour chaque combinaison, le meme chemin que runner.run_train : WARMUP > len(candles) refuse
    (tout serait force a 0, 0 trade sans explication), check_causality, period_targets avec un
    historique vide (le train n'a aucune bougie avant 2021-01-01), puis gate.evaluate. Les memes
    fonctions, pas une copie : le balayage juge exactement ce que run_train jugera.
    """
    name_a, name_b = names
    results = []
    for a, b in grid:
        strategy = make_strategy(targets_fn, a, b)
        if strategy.WARMUP > len(candles):
            raise ValueError(f"WARMUP ({strategy.WARMUP}) depasse le train ({len(candles)} bougies)"
                             f" pour {_label(names, a, b, ', ')}")
        check_causality(strategy, candles)
        targets = period_targets(strategy, [], candles)
        results.append({name_a: a, name_b: b, **gate.evaluate(candles, targets)})
    return results


def neighbors(grid_n, grid_m, n, m):
    """Retourne les combinaisons a un seul cran de (n, m) en N ou en M, dans l'ordre de la grille.

    Un cran = indice voisin dans grid_n ou grid_m, pas une distance en valeur : 60 -> 120 -> 240 est
    une grille geometrique, seul l'indice a un sens. Distance d'indices |di| + |dj| == 1 : exclut la
    combinaison elle-meme (0) et les diagonales (2), comme le disent donchian.md et sma-cross.md.
    Les noms n, m sont historiques : la fonction vaut pour toute grille a deux parametres (F, S...).
    """
    i, j = grid_n.index(n), grid_m.index(m)
    return [
        (grid_n[a], grid_m[b])
        for a in range(len(grid_n))
        for b in range(len(grid_m))
        if abs(a - i) + abs(b - j) == 1
    ]


def choose(results, grid_a=GRID_N, grid_b=GRID_M, names=("n", "m")):
    """Applique la regle de choix des .md et retourne le dict retenu, ou None.

    donchian.md et sma-cross.md ont la meme regle, seuls la grille et les noms des parametres
    changent : d'ou grid_a, grid_b et names, avec par defaut la grille et les cles donchian.

    Regle : candidate = passe les 4 criteres ET toutes ses voisines aussi. Plusieurs candidates :
    celle au final_normal le plus eleve. Aucune : None (idee abandonnee). Exiger les voisines
    ecarte un pic isole, qui a plus de chances d'etre du bruit que d'un avantage reel.

    Fonction pure : ne lit que results. ChoiceRuleError si results ne couvre pas exactement le
    produit de grid_a et grid_b (une voisine absente ne peut pas etre jugee, la regle suppose la
    grille complete), ou si plusieurs candidates sont a egalite exacte sur le meilleur final_normal
    (la regle ne dit pas laquelle prendre, et choisir apres avoir vu les chiffres est justement ce
    qu'elle interdit).
    """
    name_a, name_b = names
    grid = product_grid(grid_a, grid_b)
    by_combo = {(r[name_a], r[name_b]): r for r in results}
    if len(results) != len(grid) or set(by_combo) != set(grid):
        raise ChoiceRuleError(f"les resultats doivent couvrir exactement les {len(grid)} combinaisons de la grille")

    candidates = [
        r for r in results
        if r["passed"] and all(by_combo[v]["passed"] for v in neighbors(grid_a, grid_b, r[name_a], r[name_b]))
    ]
    if not candidates:
        return None
    best = max(r["final_normal"] for r in candidates)
    top = [r for r in candidates if r["final_normal"] == best]
    if len(top) > 1:
        combos = ", ".join(_label(names, r[name_a], r[name_b]) for r in top)
        raise ChoiceRuleError(f"egalite exacte de final_normal ({best}) entre {combos} : cas non couvert par la regle")
    return top[0]


def _print_table(results, names=("n", "m")):
    # Montants a 2 decimales : le gate P2 compare a 0,01 USDT pres, plus de precision n'apporte rien.
    # En-tete = cles des resultats, en minuscules : pour donchian "   n    m", comme avant.
    name_a, name_b = names
    print(f"{name_a:>4} {name_b:>4} {'n_trades':>8} {'final_normal':>13} {'final_doubled':>13} {'final_bh':>13}"
          f" {'c1':>5} {'c2':>5} {'c3':>5} {'c4':>5} {'passed':>6}")
    for r in results:
        print(f"{r[name_a]:>4} {r[name_b]:>4} {r['n_trades']:>8} {r['final_normal']:>13.2f} {r['final_doubled']:>13.2f}"
              f" {r['final_bh']:>13.2f} {r['c1']!s:>5} {r['c2']!s:>5} {r['c3']!s:>5} {r['c4']!s:>5} {r['passed']!s:>6}")


def main(argv=None):
    """Point d'entree : python -m backtester.sweep <nom>, nom parmi les cles de STRATEGIES.

    Nom obligatoire, restreint par choices : sans nom ou avec un nom inconnu, argparse refuse
    (SystemExit) avant toute lecture de data/. Pas de valeur par defaut : balayer donchian en
    croyant balayer sma-cross donnerait un tableau trompeur. Un argument en trop ("test"...) est
    refuse au lieu d'etre ignore en silence. Meme ordre que run_train : fichier present, hash
    verifie avant de lire une bougie (le choix doit porter sur les donnees verifiees en P1), puis
    load_train.

    La fonction de cibles (STRATEGIES[nom]["targets"]) est recuperee par runner.load_strategy puis
    getattr, et non par un import : c'est le meme chargement que pour le run train et le run test,
    avec les memes controles d'imports.

    ValueError (donc ChoiceRuleError) : refus attendu, une ligne sur stderr et code 1, comme
    runner.main. Le tableau est affiche avant le verdict : en cas d'egalite, les 9 lignes restent
    visibles pour que je tranche a la main.
    """
    parser = argparse.ArgumentParser(prog="python -m backtester.sweep")
    parser.add_argument("name", choices=list(STRATEGIES))
    args = parser.parse_args(argv)
    config = STRATEGIES[args.name]
    names = config["names"]
    grid_a, grid_b = config["grids"]

    try:
        if not Path(DATA_PATH).is_file():
            raise ValueError(f"donnees introuvables : {DATA_PATH}")
        check_data_hash(DATA_PATH, DATA_SHA256)
        candles = load_train(DATA_PATH)
        strategy = load_strategy(strategy_path(args.name, STRATEGIES_DIR))
        targets_fn = getattr(strategy, config["targets"], None)
        if not callable(targets_fn):
            raise ValueError(f"{config['targets']} absent ou non appelable dans la strategie {args.name}")
        results = sweep(candles, product_grid(grid_a, grid_b), targets_fn, names)
        _print_table(results, names)
        chosen = choose(results, grid_a, grid_b, names)
        if chosen is None:
            print("AUCUNE : idee abandonnee")
        else:
            # Pour donchian : "RETENUE : N=..., M=... (final_normal ...)", exactement comme avant.
            print(f"RETENUE : {_label(names, chosen[names[0]], chosen[names[1]], ', ')}"
                  f" (final_normal {chosen['final_normal']:.2f})")
    except ValueError as e:
        message = " ; ".join(line for line in str(e).splitlines() if line.strip())
        print(f"erreur : {message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
