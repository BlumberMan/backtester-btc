import pytest

from backtester.clean import CLEAN_HEADER, to_utc_str
from backtester.data import STEP_MS, TRAIN_END_MS, TRAIN_START_MS, load_train

T0 = 1609459200000  # 2021-01-01T00:00:00Z
STEP = 14400000  # 4h
LAST_TRAIN = 1704052800000  # 2023-12-31T20:00:00Z
FIRST_TEST = 1704067200000  # 2024-01-01T00:00:00Z
TRAIN_COUNT = 6570  # 1095 jours x 6 bougies


def line(open_time):
    return f"{open_time},{to_utc_str(open_time)},29000.01000000,29500.50000000,28800.00000000,29400.12000000,1234.56789000"


def write_csv(tmp_path, lines, header=True):
    path = tmp_path / "BTCUSDT_4h.csv"
    content = ([",".join(CLEAN_HEADER)] if header else []) + lines
    path.write_text("".join(l + "\n" for l in content), encoding="utf-8")
    return path


def full_train_lines():
    return [line(t) for t in range(T0, FIRST_TEST, STEP)]


def test_train_end_constant():
    assert TRAIN_END_MS == 1704067200000


def test_train_start_constant():
    assert TRAIN_START_MS == 1609459200000


def test_step_constant():
    assert STEP_MS == 14400000


def test_last_train_candle_included_and_test_candles_excluded(tmp_path):
    lines = full_train_lines() + [line(FIRST_TEST), line(FIRST_TEST + STEP), line(FIRST_TEST + 2 * STEP)]
    candles = load_train(write_csv(tmp_path, lines))
    assert len(candles) == TRAIN_COUNT
    assert candles[0][0] == 1609459200000
    assert candles[-1][0] == 1704052800000
    assert all(c[0] < 1704067200000 for c in candles)


def test_file_ending_exactly_at_last_train_candle(tmp_path):
    candles = load_train(write_csv(tmp_path, full_train_lines()))
    assert len(candles) == TRAIN_COUNT
    assert candles[-1][0] == LAST_TRAIN


def test_tuple_format(tmp_path):
    candles = load_train(write_csv(tmp_path, [line(T0), line(T0 + STEP)]))
    assert candles[0] == (1609459200000, 29000.01, 29500.5, 28800.0, 29400.12)
    for c in candles:
        assert len(c) == 5
        assert type(c[0]) is int
        assert all(type(x) is float for x in c[1:])


def test_corrupted_line_after_train_end_is_never_read(tmp_path):
    lines = full_train_lines() + [line(FIRST_TEST), "ligne;illisible;@@@", "abc,def"]
    candles = load_train(write_csv(tmp_path, lines))
    assert candles[-1][0] == LAST_TRAIN


def test_first_candle_not_train_start_raises(tmp_path):
    with pytest.raises(ValueError):
        load_train(write_csv(tmp_path, [line(T0 + STEP), line(T0 + 2 * STEP)]))


def test_first_candle_before_train_start_raises(tmp_path):
    with pytest.raises(ValueError):
        load_train(write_csv(tmp_path, [line(T0 - STEP), line(T0)]))


def test_gap_raises(tmp_path):
    with pytest.raises(ValueError):
        load_train(write_csv(tmp_path, [line(T0), line(T0 + STEP), line(T0 + 3 * STEP)]))


def test_duplicate_raises(tmp_path):
    with pytest.raises(ValueError):
        load_train(write_csv(tmp_path, [line(T0), line(T0 + STEP), line(T0 + STEP)]))


def test_empty_file_raises(tmp_path):
    with pytest.raises(ValueError):
        load_train(write_csv(tmp_path, [], header=False))


def test_header_only_raises(tmp_path):
    with pytest.raises(ValueError):
        load_train(write_csv(tmp_path, []))


def test_only_test_candles_raises(tmp_path):
    with pytest.raises(ValueError):
        load_train(write_csv(tmp_path, [line(FIRST_TEST), line(FIRST_TEST + STEP)]))
