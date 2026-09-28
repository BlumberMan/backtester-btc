from backtester.__main__ import check_python_version, main


def test_check_python_version_accepts_3_14():
    assert check_python_version((3, 14, 7)) is True


def test_check_python_version_rejects_3_13():
    assert check_python_version((3, 13, 5)) is False


def test_check_python_version_rejects_4_14():
    assert check_python_version((4, 14, 0)) is False


def test_main_prints_version(capsys):
    assert main() == 0
    # capsys capture ce que main() a écrit sur la sortie standard
    output = capsys.readouterr().out
    assert "backtester-btc v0.1.0" in output
