import pytest

from backtester.clean import CLEAN_HEADER, to_utc_str
from backtester.holdout import TEST_COUNT, TEST_END_MS, TEST_START_MS, load_test

T0 = 1609459200000  # 2021-01-01T00:00:00Z
STEP = 14400000  # 4h
LAST_TRAIN = 1704052800000  # 2023-12-31T20:00:00Z
FIRST_TEST = 1704067200000  # 2024-01-01T00:00:00Z
LAST_TEST = 1788206400000  # 2026-08-31T20:00:00Z
AFTER_TEST = 1788220800000  # 2026-09-01T00:00:00Z


def line(open_time):
    return f"{open_time},{to_utc_str(open_time)},29000.01000000,29500.50000000,28800.00000000,29400.12000000,1234.56789000"


def write_csv(tmp_path, lines, header=True):
    path = tmp_path / "BTCUSDT_4h.csv"
    content = ([",".join(CLEAN_HEADER)] if header else []) + lines
    path.write_text("".join(l + "\n" for l in content), encoding="utf-8")
    return path


def full_lines():
    """12414 bougies : 6570 de train + 5844 de test."""
    return [line(t) for t in range(T0, AFTER_TEST, STEP)]


def test_test_start_constant():
    assert TEST_START_MS == 1704067200000


def test_test_end_constant():
    assert TEST_END_MS == 1788220800000


def test_test_count_constant():
    assert TEST_COUNT == 5844


def test_full_grid_count():
    assert len(full_lines()) == 12414


def test_full_grid_warmup_50(tmp_path):
    warmup_candles, test_candles = load_test(write_csv(tmp_path, full_lines()), 50)
    assert len(test_candles) == 5844
    assert test_candles[0][0] == 1704067200000
    assert test_candles[-1][0] == 1788206400000
    assert len(warmup_candles) == 50
    assert warmup_candles[-1][0] == 1704052800000
    assert warmup_candles[0][0] == 1704052800000 - 49 * 14400000


def test_warmup_zero_returns_empty_list(tmp_path):
    warmup_candles, test_candles = load_test(write_csv(tmp_path, full_lines()), 0)
    assert warmup_candles == []
    assert len(test_candles) == 5844


def test_warmup_whole_train_accepted(tmp_path):
    warmup_candles, test_candles = load_test(write_csv(tmp_path, full_lines()), 6570)
    assert len(warmup_candles) == 6570
    assert warmup_candles[0][0] == 1609459200000
    assert warmup_candles[-1][0] == 1704052800000


@pytest.mark.parametrize("warmup", [6571, -1, 1.5])
def test_invalid_warmup_raises(tmp_path, warmup):
    with pytest.raises(ValueError):
        load_test(write_csv(tmp_path, full_lines()), warmup)


def test_tuple_format(tmp_path):
    warmup_candles, test_candles = load_test(write_csv(tmp_path, full_lines()), 1)
    assert test_candles[0] == (1704067200000, 29000.01, 29500.5, 28800.0, 29400.12)
    assert warmup_candles[0] == (1704052800000, 29000.01, 29500.5, 28800.0, 29400.12)
    for c in warmup_candles + test_candles:
        assert len(c) == 5
        assert type(c[0]) is int
        assert all(type(x) is float for x in c[1:])


def test_corrupted_line_after_test_end_is_never_read(tmp_path):
    lines = full_lines() + [line(AFTER_TEST), "ligne;illisible;@@@", "abc,def"]
    _, test_candles = load_test(write_csv(tmp_path, lines), 50)
    assert len(test_candles) == 5844
    assert test_candles[-1][0] == LAST_TEST


def test_gap_in_train_raises(tmp_path):
    lines = [l for l in full_lines() if not l.startswith(f"{T0 + 100 * STEP},")]
    with pytest.raises(ValueError):
        load_test(write_csv(tmp_path, lines), 50)


def test_gap_at_train_test_junction_raises(tmp_path):
    lines = [l for l in full_lines() if not l.startswith(f"{FIRST_TEST},")]
    with pytest.raises(ValueError):
        load_test(write_csv(tmp_path, lines), 50)


def test_gap_at_last_train_candle_raises(tmp_path):
    lines = [l for l in full_lines() if not l.startswith(f"{LAST_TRAIN},")]
    with pytest.raises(ValueError):
        load_test(write_csv(tmp_path, lines), 50)


def test_duplicate_in_train_raises(tmp_path):
    lines = full_lines()
    lines.insert(11, line(T0 + 10 * STEP))
    with pytest.raises(ValueError):
        load_test(write_csv(tmp_path, lines), 50)


def test_duplicate_in_test_raises(tmp_path):
    lines = full_lines()
    lines.insert(6571, line(FIRST_TEST))
    with pytest.raises(ValueError):
        load_test(write_csv(tmp_path, lines), 50)


def test_first_candle_not_train_start_raises(tmp_path):
    with pytest.raises(ValueError):
        load_test(write_csv(tmp_path, full_lines()[1:]), 0)


def test_truncated_test_raises(tmp_path):
    with pytest.raises(ValueError):
        load_test(write_csv(tmp_path, full_lines()[:-1]), 50)


def test_truncated_test_then_candle_after_end_raises(tmp_path):
    lines = full_lines()[:-1] + [line(AFTER_TEST)]
    with pytest.raises(ValueError):
        load_test(write_csv(tmp_path, lines), 50)


def test_train_only_raises(tmp_path):
    lines = [line(t) for t in range(T0, FIRST_TEST, STEP)]
    with pytest.raises(ValueError):
        load_test(write_csv(tmp_path, lines), 50)


def test_header_only_raises(tmp_path):
    with pytest.raises(ValueError):
        load_test(write_csv(tmp_path, []), 0)
