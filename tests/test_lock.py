import subprocess

import pytest

from backtester.lock import LockError, append_result, check_lock, name_in_results, validate_name


def git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    """Depot git temporaire : un commit initial portant le tag test-ema. Le fichier de
    resultats est hors du depot pour ne pas salir l'arbre."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "core.autocrlf", "false")
    (repo / "strategie.py").write_text("WARMUP = 50\n", encoding="utf-8")
    git(repo, "add", "strategie.py")
    git(repo, "commit", "-m", "initial")
    git(repo, "tag", "test-ema")
    return repo


@pytest.fixture
def results(tmp_path):
    return tmp_path / "resultats_test.md"


# validate_name

@pytest.mark.parametrize("name", ["ema-50", "rsi_14"])
def test_validate_name_accepte(name):
    validate_name(name)


@pytest.mark.parametrize("name", ["", "Ema", "a b", "-x", "a;b", "../x"])
def test_validate_name_refuse(name):
    with pytest.raises(LockError):
        validate_name(name)


# name_in_results

def test_name_in_results_present():
    assert name_in_results("ema", "# Resultats\n\n## ema\n- capital: 1000\n") is True


def test_name_in_results_ema_v2_ne_bloque_pas_ema():
    assert name_in_results("ema", "## ema_v2\n- capital: 1000\n") is False


def test_name_in_results_autres_lignes():
    assert name_in_results("ema", "- ema\nla strategie ema a ete testee\n### ema\n") is False


# check_lock

def test_check_lock_passe(repo, results):
    results.write_text("## rsi\n- capital: 900\n\n", encoding="utf-8")
    check_lock("ema", repo, results)


def test_check_lock_fichier_results_absent_passe(repo, results):
    assert not results.exists()
    check_lock("ema", repo, results)


def test_check_lock_nom_invalide(repo, results):
    with pytest.raises(LockError, match="invalide"):
        check_lock("Ema", repo, results)


def test_check_lock_tag_absent(repo, results):
    with pytest.raises(LockError, match="absent"):
        check_lock("rsi", repo, results)


def test_check_lock_head_different_du_tag(repo, results):
    (repo / "strategie.py").write_text("WARMUP = 60\n", encoding="utf-8")
    git(repo, "commit", "-am", "apres le tag")
    with pytest.raises(LockError, match="HEAD"):
        check_lock("ema", repo, results)


def test_check_lock_fichier_modifie(repo, results):
    (repo / "strategie.py").write_text("WARMUP = 60\n", encoding="utf-8")
    with pytest.raises(LockError, match="non propre"):
        check_lock("ema", repo, results)


def test_check_lock_fichier_non_suivi(repo, results):
    (repo / "nouveau.py").write_text("x = 1\n", encoding="utf-8")
    with pytest.raises(LockError, match="non propre"):
        check_lock("ema", repo, results)


def test_check_lock_nom_deja_dans_results(repo, results):
    results.write_text("## ema\n- capital: 1000\n\n", encoding="utf-8")
    with pytest.raises(LockError, match="deja"):
        check_lock("ema", repo, results)


# append_result

def test_append_result_section(results):
    append_result("ema", {"capital_final": 1234.5, "trades": 31}, results)
    assert results.read_bytes() == b"## ema\n- capital_final: 1234.5\n- trades: 31\n\n"


def test_append_result_deux_sections(results):
    append_result("ema", {"trades": 31}, results)
    append_result("rsi", {"trades": 40}, results)
    assert results.read_bytes() == b"## ema\n- trades: 31\n\n## rsi\n- trades: 40\n\n"


def test_append_result_puis_name_in_results(results):
    append_result("ema", {"trades": 31}, results)
    assert name_in_results("ema", results.read_text(encoding="utf-8")) is True
