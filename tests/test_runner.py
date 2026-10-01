import ast
import hashlib
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import backtester.holdout
from backtester.clean import CLEAN_HEADER, to_utc_str
from backtester.lock import LockError
import backtester.runner
from backtester.runner import (
    DATA_SHA256, MAX_CUTS, _check_cuts, check_causality, check_data_hash, load_strategy, main,
    period_targets, run_test, run_train,
)

T0 = 1609459200000  # 2021-01-01T00:00:00Z
STEP = 14400000  # 4h
FIRST_TEST = 1704067200000  # 2024-01-01T00:00:00Z
AFTER_TEST = 1788220800000  # 2026-09-01T00:00:00Z

BACKTESTER_DIR = Path(__file__).resolve().parent.parent / "backtester"
RUNNER_PY = BACKTESTER_DIR / "runner.py"
README = BACKTESTER_DIR.parent / "README.md"

VALID = "WARMUP = 10\n\ndef compute_targets(candles):\n    return [0] * len(candles)\n"


def strategy_source(warmup, target):
    return f"WARMUP = {warmup}\n\ndef compute_targets(candles):\n    return [{target}] * len(candles)\n"


def line(open_time):
    """Prix constants : le resultat ne depend que des frais, du slippage et du nombre de trades."""
    return f"{open_time},{to_utc_str(open_time)},29000.00000000,29000.00000000,29000.00000000,29000.00000000,1234.56789000"


def write_csv(path, end):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [",".join(CLEAN_HEADER)] + [line(t) for t in range(T0, end, STEP)]
    path.write_text("".join(l + "\n" for l in lines), encoding="utf-8")
    return path


def write_rising_csv(path, end):
    """Prix strictement croissants (+1 par bougie) : une strategie qui lit la bougie suivante
    change de cible quand on la retire, ce que les prix constants de write_csv ne montreraient pas."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [",".join(CLEAN_HEADER)]
    for i, t in enumerate(range(T0, end, STEP)):
        p = f"{10000 + i}.00000000"
        lines.append(f"{t},{to_utc_str(t)},{p},{p},{p},{p},1234.56789000")
    path.write_text("".join(l + "\n" for l in lines), encoding="utf-8")
    return path


CAUSAL = (
    "WARMUP = 0\n\n"
    "def compute_targets(candles):\n"
    "    return [1 if i >= 1 and candles[i][4] > candles[i - 1][4] else 0 for i in range(len(candles))]\n"
)

CHEAT = (
    "WARMUP = 0\n\n"
    "def compute_targets(candles):\n"
    "    return [1 if i + 1 < len(candles) and candles[i + 1][4] > candles[i][4] else 0 for i in range(len(candles))]\n"
)


def rising_candles(n):
    return [(T0 + i * STEP, 100.0 + i, 100.0 + i, 100.0 + i, 100.0 + i) for i in range(n)]


def sha256(path):
    """Hash attendu calcule independamment de runner.check_data_hash."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def candles(n):
    return [(T0 + i * STEP, 1.0, 1.0, 1.0, 1.0) for i in range(n)]


def fake(warmup, target, received=None):
    def compute_targets(cs):
        if received is not None:
            received.append(len(cs))
        return [target] * len(cs)

    return SimpleNamespace(WARMUP=warmup, compute_targets=compute_targets)


# period_targets

def test_period_targets_sans_historique_force_le_warmup():
    assert period_targets(fake(10, 1), [], candles(30)) == [0] * 10 + [1] * 20


def test_period_targets_historique_suffisant_aucun_forcage():
    assert period_targets(fake(10, 1), candles(10), candles(30)) == [1] * 30


def test_period_targets_warmup_zero():
    assert period_targets(fake(0, 1), [], candles(30)) == [1] * 30


def test_period_targets_recoit_history_plus_period():
    received = []
    period_targets(fake(10, 1, received), candles(10), candles(30))
    assert received == [40]


@pytest.mark.parametrize("bad", [
    lambda cs: [0] * (len(cs) - 1),
    lambda cs: [0] * (len(cs) - 1) + [2],
    lambda cs: [0] * (len(cs) - 1) + [True],
    lambda cs: [0] * (len(cs) - 1) + [1.0],
])
def test_period_targets_cibles_invalides(bad):
    with pytest.raises(ValueError):
        period_targets(SimpleNamespace(WARMUP=0, compute_targets=bad), [], candles(30))


# load_strategy

def test_load_strategy_valide(tmp_path):
    module = load_strategy(write_file(tmp_path / "ema.py", VALID))
    assert module.WARMUP == 10
    assert module.compute_targets([1, 2, 3]) == [0, 0, 0]


def test_load_strategy_nom_avec_tiret(tmp_path):
    module = load_strategy(write_file(tmp_path / "ema-50.py", VALID))
    assert module.WARMUP == 10


@pytest.mark.parametrize("content", [
    "import numpy\n" + VALID,
    "import backtester.engine\n" + VALID,
    "from backtester.engine import run_backtest\n" + VALID,
    "open('data/BTCUSDT_4h.csv')\n" + VALID,
    "def compute_targets(candles):\n    return [0] * len(candles)\n",
    "WARMUP = True\n\ndef compute_targets(candles):\n    return [0] * len(candles)\n",
    "WARMUP = -1\n\ndef compute_targets(candles):\n    return [0] * len(candles)\n",
    "WARMUP = 10\n",
])
def test_load_strategy_refuse(tmp_path, content):
    with pytest.raises(ValueError):
        load_strategy(write_file(tmp_path / "bad.py", content))


@pytest.mark.parametrize("imp", ["import os", "import pathlib", "import subprocess", "from pathlib import Path"])
def test_load_strategy_refuse_stdlib_hors_liste_blanche(tmp_path, imp):
    with pytest.raises(ValueError, match="modules autorises"):
        load_strategy(write_file(tmp_path / "bad.py", imp + "\n" + VALID))


@pytest.mark.parametrize("imp", ["import math", "from statistics import mean", "from collections import deque"])
def test_load_strategy_accepte_liste_blanche(tmp_path, imp):
    assert load_strategy(write_file(tmp_path / "ok.py", imp + "\n" + VALID)).WARMUP == 10


def test_load_strategy_fichier_absent(tmp_path):
    with pytest.raises(ValueError):
        load_strategy(tmp_path / "absent.py")


# check_causality

def strategy_from(source):
    namespace = {}
    exec(source, namespace)
    return SimpleNamespace(WARMUP=namespace["WARMUP"], compute_targets=namespace["compute_targets"])


def test_check_causality_strategie_causale_passe():
    check_causality(strategy_from(CAUSAL), rising_candles(50))


def test_check_causality_strategie_tricheuse_refusee():
    with pytest.raises(ValueError, match="lookahead"):
        check_causality(strategy_from(CHEAT), rising_candles(50))


def jump_candles(n, jumps):
    """Prix constants a 100, sauf un saut de +10 % (qui reste) a chaque index de jumps."""
    out, price = [], 100.0
    for i in range(n):
        if i in jumps:
            price *= 1.1
        out.append((T0 + i * STEP, price, price, price, price))
    return out


RARE_CHEAT = (
    "WARMUP = 0\n\n"
    "def compute_targets(candles):\n"
    "    return [1 if i + 1 < len(candles) and candles[i + 1][4] > candles[i][4] * 1.05 else 0\n"
    "            for i in range(len(candles))]\n"
)


def test_check_causality_tricheuse_rare_refusee_mais_passait_l_ancienne_methode():
    # Sauts a 500, 1200, 1700 : la triche porte sur les cibles 499, 1199, 1699, hors des
    # index {0, 1, 9, 99, 999, 998, 1998} que verifiaient les 7 anciennes coupures.
    cs = jump_candles(2000, {500, 1200, 1700})
    strategy = strategy_from(RARE_CHEAT)
    full = strategy.compute_targets(cs)
    assert [i for i, t in enumerate(full) if t == 1] == [499, 1199, 1699]

    _check_cuts(strategy, cs, full, [1, 2, 10, 100, 1000, 1000, 1999])  # ancienne methode : passe
    with pytest.raises(ValueError, match="lookahead detecte : la cible a l'index 499"):
        check_causality(strategy, cs)


def test_check_causality_nombre_d_appels_borne():
    # Cible alternee (causale) : 998 points de decision, la reduction a MAX_CUTS doit s'appliquer.
    calls = []

    def compute_targets(cs):
        calls.append(len(cs))
        return [i % 2 for i in range(len(cs))]

    check_causality(SimpleNamespace(WARMUP=0, compute_targets=compute_targets), candles(1000))
    assert MAX_CUTS == 300
    assert len(calls) <= 301
    assert calls[0] == 1000


# check_data_hash

def test_check_data_hash_bon_hash(tmp_path):
    path = tmp_path / "x.csv"
    path.write_bytes(b"a,b\n1,2\n")
    check_data_hash(path, hashlib.sha256(b"a,b\n1,2\n").hexdigest())


def test_check_data_hash_hash_faux(tmp_path):
    path = tmp_path / "x.csv"
    path.write_bytes(b"a,b\n1,2\n")
    with pytest.raises(ValueError, match="0" * 64):
        check_data_hash(path, "0" * 64)


def test_data_sha256_ecrit_dans_le_readme():
    assert DATA_SHA256 in README.read_text(encoding="utf-8")


# run_train

@pytest.fixture
def train_dir(tmp_path):
    write_csv(tmp_path / "BTCUSDT_4h.csv", FIRST_TEST)  # 6570 bougies
    return tmp_path


def test_run_train_toujours_0(train_dir):
    write_file(train_dir / "strategies" / "zero.py", strategy_source(0, 0))
    result = run_train("zero", train_dir / "BTCUSDT_4h.csv", train_dir / "strategies", sha256(train_dir / "BTCUSDT_4h.csv"))
    assert result["warmup"] == 0
    assert result["final_normal"] == 1000.0
    assert result["n_trades"] == 0
    assert result["c1"] is False
    assert result["passed"] is False


def test_run_train_toujours_1_warmup_5(train_dir):
    write_file(train_dir / "strategies" / "un.py", strategy_source(5, 1))
    result = run_train("un", train_dir / "BTCUSDT_4h.csv", train_dir / "strategies", sha256(train_dir / "BTCUSDT_4h.csv"))
    assert result["warmup"] == 5
    assert result["n_trades"] == 1


@pytest.fixture
def rising_dir(tmp_path):
    write_rising_csv(tmp_path / "BTCUSDT_4h.csv", FIRST_TEST)  # 6570 bougies
    return tmp_path


def test_run_train_strategie_tricheuse_refusee(rising_dir):
    write_file(rising_dir / "strategies" / "cheat.py", CHEAT)
    with pytest.raises(ValueError, match="lookahead"):
        run_train("cheat", rising_dir / "BTCUSDT_4h.csv", rising_dir / "strategies", sha256(rising_dir / "BTCUSDT_4h.csv"))


def test_run_train_strategie_causale_passe(rising_dir):
    write_file(rising_dir / "strategies" / "causal.py", CAUSAL)
    result = run_train("causal", rising_dir / "BTCUSDT_4h.csv", rising_dir / "strategies", sha256(rising_dir / "BTCUSDT_4h.csv"))
    assert result["warmup"] == 0


def test_run_train_hash_faux(train_dir):
    write_file(train_dir / "strategies" / "zero.py", strategy_source(0, 0))
    with pytest.raises(ValueError, match="hash"):
        run_train("zero", train_dir / "BTCUSDT_4h.csv", train_dir / "strategies", "0" * 64)


def test_run_train_warmup_plus_long_que_le_train(train_dir):
    write_file(train_dir / "strategies" / "long.py", strategy_source(7000, 0))
    with pytest.raises(ValueError, match="WARMUP"):
        run_train("long", train_dir / "BTCUSDT_4h.csv", train_dir / "strategies", sha256(train_dir / "BTCUSDT_4h.csv"))


# run_test

@pytest.fixture
def setup(tmp_path):
    """Depot git temporaire avec la strategie zero commitee et taggee test-zero. Le CSV
    (12414 bougies) et le fichier de resultats sont hors du depot pour garder l'arbre propre."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "core.autocrlf", "false")
    write_file(repo / "backtester" / "strategies" / "zero.py", strategy_source(3, 0))
    git(repo, "add", ".")
    git(repo, "commit", "-m", "strategie zero")
    git(repo, "tag", "test-zero")
    return SimpleNamespace(
        repo=repo,
        strategies=repo / "backtester" / "strategies",
        data=write_csv(tmp_path / "data" / "BTCUSDT_4h.csv", AFTER_TEST),
        results=tmp_path / "resultats_test.md",
    )


def test_run_test_succes_ecrit_le_resultat(setup):
    result = run_test("zero", setup.data, setup.strategies, setup.repo, setup.results, sha256(setup.data))
    assert result["warmup"] == 3
    assert result["n_trades"] == 0
    lines = setup.results.read_text(encoding="utf-8").splitlines()
    assert "## zero" in lines
    assert "- warmup: 3" in lines


def test_run_test_deuxieme_appel_refuse(setup):
    run_test("zero", setup.data, setup.strategies, setup.repo, setup.results, sha256(setup.data))
    with pytest.raises(LockError, match="deja"):
        run_test("zero", setup.data, setup.strategies, setup.repo, setup.results, sha256(setup.data))


def test_run_test_tag_absent_aucune_ecriture(setup):
    git(setup.repo, "tag", "-d", "test-zero")
    with pytest.raises(LockError):
        run_test("zero", setup.data, setup.strategies, setup.repo, setup.results, sha256(setup.data))
    assert not setup.results.exists()


def test_run_test_n_appelle_pas_check_causality(setup, monkeypatch):
    def interdit(*args, **kwargs):
        raise AssertionError("check_causality appele par run_test")

    monkeypatch.setattr(backtester.runner, "check_causality", interdit)
    result = run_test("zero", setup.data, setup.strategies, setup.repo, setup.results, sha256(setup.data))
    assert result["n_trades"] == 0


def test_run_test_verrou_refuse_test_jamais_lu(setup, monkeypatch):
    def interdit(*args, **kwargs):
        raise AssertionError("load_test appele alors que le verrou refuse")

    monkeypatch.setattr(backtester.holdout, "load_test", interdit)
    git(setup.repo, "tag", "-d", "test-zero")
    with pytest.raises(LockError):
        run_test("zero", setup.data, setup.strategies, setup.repo, setup.results, sha256(setup.data))


def test_run_test_hash_faux_test_jamais_lu(setup, monkeypatch):
    def interdit(*args, **kwargs):
        raise AssertionError("load_test appele alors que le hash est faux")

    monkeypatch.setattr(backtester.holdout, "load_test", interdit)
    with pytest.raises(ValueError, match="hash"):
        run_test("zero", setup.data, setup.strategies, setup.repo, setup.results, "0" * 64)
    assert not setup.results.exists()


# gardes

def test_load_test_mentionne_seulement_dans_holdout_et_runner():
    files = {p.name for p in BACKTESTER_DIR.glob("*.py") if "load_test" in p.read_text(encoding="utf-8")}
    assert files == {"holdout.py", "runner.py"}


def test_runner_n_importe_pas_holdout_au_niveau_module():
    tree = ast.parse(RUNNER_PY.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Import):
            assert all("holdout" not in a.name for a in node.names)
        if isinstance(node, ast.ImportFrom):
            assert "holdout" not in (node.module or "")
            assert all("holdout" not in a.name for a in node.names)


# main

def test_main_train(train_dir, monkeypatch, capsys):
    write_file(train_dir / "data" / "BTCUSDT_4h.csv", (train_dir / "BTCUSDT_4h.csv").read_text(encoding="utf-8"))
    write_file(train_dir / "backtester" / "strategies" / "zero.py", strategy_source(0, 0))
    monkeypatch.setattr(backtester.runner, "DATA_SHA256", sha256(train_dir / "data" / "BTCUSDT_4h.csv"))
    monkeypatch.chdir(train_dir)
    assert main(["train", "zero"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert "warmup: 0" in out
    assert "n_trades: 0" in out
    assert "final_normal: 1000.0" in out
    assert "passed: False" in out


@pytest.fixture
def cli_repo(tmp_path):
    """Depot organise comme le vrai : data/ ignore par git, docs/ cree mais vide."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "core.autocrlf", "false")
    write_file(repo / ".gitignore", "data/\n")
    write_file(repo / "backtester" / "strategies" / "zero.py", strategy_source(3, 0))
    git(repo, "add", ".")
    git(repo, "commit", "-m", "strategie zero")
    git(repo, "tag", "test-zero")
    write_csv(repo / "data" / "BTCUSDT_4h.csv", AFTER_TEST)
    (repo / "docs").mkdir()
    return repo


def test_main_test_puis_verrou(cli_repo, monkeypatch, capsys):
    monkeypatch.setattr(backtester.runner, "DATA_SHA256", sha256(cli_repo / "data" / "BTCUSDT_4h.csv"))
    monkeypatch.chdir(cli_repo)
    assert main(["test", "zero"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert "warmup: 3" in out
    assert out[-1] == (
        "Resultat ecrit dans docs/resultats_test.md : commite-le MAINTENANT "
        "(git add docs/resultats_test.md, git commit)"
    )
    assert "## zero" in (cli_repo / "docs" / "resultats_test.md").read_text(encoding="utf-8").splitlines()

    # Le fichier de resultats non commite salit l'arbre : on le commite comme le demande le rappel,
    # puis on replace le tag sur ce commit pour que seul le controle "deja teste" puisse refuser.
    git(cli_repo, "add", "docs/resultats_test.md")
    git(cli_repo, "commit", "-m", "resultat zero")
    git(cli_repo, "tag", "-f", "test-zero")
    assert main(["test", "zero"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    # check_lock affiche le chemin via Path : separateur "\" sous Windows, "/" ailleurs.
    expected_path = Path("docs/resultats_test.md")
    assert captured.err == f"erreur : zero figure deja dans {expected_path} : le test a deja ete fait\n"


def test_main_tag_absent_code_1(cli_repo, monkeypatch, capsys):
    git(cli_repo, "tag", "-d", "test-zero")
    monkeypatch.chdir(cli_repo)
    assert main(["test", "zero"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("erreur : tag test-zero absent")
    assert err.count("\n") == 1
    assert not (cli_repo / "docs" / "resultats_test.md").exists()
