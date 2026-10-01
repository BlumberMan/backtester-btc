import os
import re
import subprocess
from pathlib import Path

# Le nom sert de nom de tag git (test-<nom>) et de titre "## <nom>" dans docs/resultats_test.md.
# Minuscules, chiffres, "_" et "-" seulement, et premier caractere alphanumerique : pas d'espace
# ni de caractere special qui casserait le tag ou le titre, pas de "-" initial qui ferait lire
# le nom comme une option par git, pas de "/" ou "." qui permettrait "../x".
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class LockError(Exception):
    """Le verrou refuse le run test. Exception dediee pour que la commande de test puisse la
    distinguer d'un bug : un refus du verrou est attendu, il n'est pas un plantage."""


def validate_name(name):
    """Leve LockError si name ne correspond pas a NAME_PATTERN.

    Verifie en premier dans check_lock : le nom est ensuite passe a git et ecrit dans le fichier
    de resultats, un nom invalide ne doit atteindre ni l'un ni l'autre.
    fullmatch et non match : avec match, "$" accepte un "\\n" final, donc "ema\\n" passerait.
    """
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        raise LockError(f"nom de strategie invalide : {name!r} (attendu : {NAME_PATTERN.pattern})")


def name_in_results(name, results_text):
    """Vrai si une ligne de results_text est exactement "## <name>" (apres strip).

    Comparaison de ligne entiere, jamais de sous-chaine : "ema" ne doit pas etre bloque par
    "## ema_v2", ni par une ligne "- ema" ou un texte qui mentionne ema. Un faux positif
    bloquerait a tort une strategie qui n'a jamais ete testee.
    """
    title = f"## {name}"
    return any(line.strip() == title for line in results_text.splitlines())


def _git(repo_dir, *args):
    """Lance git avec une liste d'arguments (jamais shell=True : le nom n'est jamais interprete
    par un shell) dans repo_dir et retourne stdout sans espaces de bord.

    Leve LockError si git echoue (pas un depot, git absent, ref inconnue) : dans le doute, le
    verrou refuse. Un verrou qui laisse passer quand il ne sait pas verifier ne protege rien.
    """
    try:
        proc = subprocess.run(["git", *args], cwd=repo_dir, capture_output=True, text=True)
    except OSError as e:
        raise LockError(f"impossible de lancer git : {e}") from e
    if proc.returncode != 0:
        raise LockError(f"git {' '.join(args)} a echoue : {proc.stderr.strip()}")
    return proc.stdout.strip()


def check_lock(name, repo_dir, results_path):
    """Leve LockError si le run test de name est interdit (SPEC, Gate P3 etapes 4 a 6 et
    "Verrou renforce"). Les verifications se font dans cet ordre, la premiere qui echoue arrete :

    1. nom invalide : il serait passe a git et ecrit dans les resultats.
    2. tag test-<name> absent : sans tag, la strategie n'a pas ete gelee (etape 4), rien ne
       prouve plus tard quel code a produit le resultat.
    3. HEAD different du commit du tag : le code execute ne serait pas le code gele, on pourrait
       tagger une version puis tester une autre.
    4. arbre non propre (fichiers non suivis inclus) : une modification non commitee, meme un
       nouveau fichier importe par la strategie, changerait le code execute sans changer HEAD.
    5. name deja dans results_path : la periode de test ne se regarde qu'une fois (etape 6).
       Fichier absent = aucun test passe, donc autorise.
    """
    validate_name(name)
    tag = f"test-{name}"

    if _git(repo_dir, "tag", "--list", tag) != tag:
        raise LockError(f"tag {tag} absent : geler la strategie (commit + git tag {tag}) avant le test")

    head = _git(repo_dir, "rev-parse", "HEAD")
    tagged = _git(repo_dir, "rev-list", "-n", "1", tag)
    if head != tagged:
        raise LockError(f"HEAD ({head[:12]}) n'est pas le commit du tag {tag} ({tagged[:12]})")

    status = _git(repo_dir, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise LockError(f"arbre git non propre :\n{status}")

    results_path = Path(results_path)
    if results_path.exists() and name_in_results(name, results_path.read_text(encoding="utf-8")):
        raise LockError(f"{name} figure deja dans {results_path} : le test a deja ete fait")


def append_result(name, result, results_path):
    """Ajoute la section de name a results_path : "## <name>", une ligne "- <cle>: <valeur>"
    par entree de result, puis une ligne vide.

    Mode "a" : les resultats precedents ne sont jamais reecrits. newline="\\n" force les fins de
    ligne LF, meme sous Windows, pour que le fichier commite soit identique partout.
    flush() puis os.fsync() avant de fermer : le resultat doit etre sur le disque avant tout
    affichage (SPEC, Plantage du run test). Sans fsync, un plantage apres l'affichage pourrait
    perdre l'ecriture alors qu'un chiffre a ete vu, et le verrou ne bloquerait pas un second run.
    """
    lines = [f"## {name}"] + [f"- {key}: {value}" for key, value in result.items()] + [""]
    with open(results_path, "a", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
        f.flush()
        os.fsync(f.fileno())
