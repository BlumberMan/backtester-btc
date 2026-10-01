import ast
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import backtester.holdout
from backtester.clean import CLEAN_HEADER, to_utc_str
from backtester.lock import LockError
from backtester.runner import load_strategy, main, period_targets, run_test, run_train

T0 = 1609459200000  # 2021-01-01T00:00:00Z
STEP = 14400000  # 4h
FIRST_TEST = 1704067200000  # 2024-01-01T00:00:00Z
AFTER_TEST = 1788220800000  # 2026-09-01T00:00:00Z

BACKTESTER_DIR = Path(__file__).resolve().parent.parent / "backtester"
RUNNER_PY = BACKTESTER_DIR / "runner.py"

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


def test_load_strategy_fichier_absent(tmp_path):
    with pytest.raises(ValueError):
        load_strategy(tmp_path / "absent.py")


# run_train

@pytest.fixture
def train_dir(tmp_path):
    write_csv(tmp_path / "BTCUSDT_4h.csv", FIRST_TEST)  # 6570 bougies
    return tmp_path


def test_run_train_toujours_0(train_dir):
    write_file(train_dir / "strategies" / "zero.py", strategy_source(0, 0))
    result = run_train("zero", train_dir / "BTCUSDT_4h.csv", train_dir / "strategies")
    assert result["warmup"] == 0
    assert result["final_normal"] == 1000.0
    assert result["n_trades"] == 0
    assert result["c1"] is False
    assert result["passed"] is False


def test_run_train_toujours_1_warmup_5(train_dir):
    write_file(train_dir / "strategies" / "un.py", strategy_source(5, 1))
    result = run_train("un", train_dir / "BTCUSDT_4h.csv", train_dir / "strategies")
    assert result["warmup"] == 5
    assert result["n_trades"] == 1


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
    result = run_test("zero", setup.data, setup.strategies, setup.repo, setup.results)
    assert result["warmup"] == 3
    assert result["n_trades"] == 0
    lines = setup.results.read_text(encoding="utf-8").splitlines()
    assert "## zero" in lines
    assert "- warmup: 3" in lines


def test_run_test_deuxieme_appel_refuse(setup):
    run_test("zero", setup.data, setup.strategies, setup.repo, setup.results)
    with pytest.raises(LockError, match="deja"):
        run_test("zero", setup.data, setup.strategies, setup.repo, setup.results)


def test_run_test_tag_absent_aucune_ecriture(setup):
    git(setup.repo, "tag", "-d", "test-zero")
    with pytest.raises(LockError):
        run_test("zero", setup.data, setup.strategies, setup.repo, setup.results)
    assert not setup.results.exists()


def test_run_test_verrou_refuse_test_jamais_lu(setup, monkeypatch):
    def interdit(*args, **kwargs):
        raise AssertionError("load_test appele alors que le verrou refuse")

    monkeypatch.setattr(backtester.holdout, "load_test", interdit)
    git(setup.repo, "tag", "-d", "test-zero")
    with pytest.raises(LockError):
        run_test("zero", setup.data, setup.strategies, setup.repo, setup.results)


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
