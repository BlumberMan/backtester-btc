import pytest

from backtester.clean import (
    count_zero_volume,
    dedupe,
    find_gaps,
    to_utc_str,
    validate,
    write_clean,
)
from backtester.download import INTERVAL_MS

T0 = 1609459200000  # 2021-01-01T00:00:00Z


def make_row(open_time, close="29400.12000000", volume="1234.56789000"):
    # Bougie cohérente : low <= min(open, close) et high >= max(open, close)
    return (open_time, "29000.01000000", "29500.50000000", "28800.00000000", close, volume)


def grid(n):
    return [T0 + i * INTERVAL_MS for i in range(n)]


def test_dedupe_removes_identical_duplicate():
    rows, removed = dedupe([make_row(T0), make_row(T0)])
    assert rows == [make_row(T0)]
    assert removed == 1


def test_dedupe_conflicting_values_raises():
    with pytest.raises(ValueError, match=str(T0)):
        dedupe([make_row(T0, close="29400.12000000"), make_row(T0, close="29300.00000000")])


def test_dedupe_sorts_by_open_time():
    t = grid(3)
    rows, removed = dedupe([make_row(t[2]), make_row(t[0]), make_row(t[1])])
    assert [r[0] for r in rows] == t
    assert removed == 0


def test_validate_open_time_not_on_grid_raises():
    bad = T0 + 1000
    with pytest.raises(ValueError, match=str(bad)):
        validate([make_row(bad)], T0, T0 + 10 * INTERVAL_MS)


def test_validate_open_time_out_of_range_raises():
    start, end = T0, T0 + 5 * INTERVAL_MS
    with pytest.raises(ValueError, match=str(start - INTERVAL_MS)):
        validate([make_row(start - INTERVAL_MS)], start, end)
    with pytest.raises(ValueError, match=str(end)):
        validate([make_row(end)], start, end)


def test_validate_incoherent_candle_raises():
    end = T0 + INTERVAL_MS
    high_below_close = (T0, "29000.00000000", "29100.00000000", "28800.00000000", "29200.00000000", "1.0")
    with pytest.raises(ValueError, match=str(T0)):
        validate([high_below_close], T0, end)
    low_above_open = (T0, "29000.00000000", "29500.00000000", "29000.01000000", "29200.00000000", "1.0")
    with pytest.raises(ValueError, match=str(T0)):
        validate([low_above_open], T0, end)


def test_validate_coherent_candles_pass():
    t = grid(3)
    validate([make_row(x) for x in t], T0, T0 + 3 * INTERVAL_MS)


def test_find_gaps_detects_missing_third_candle():
    t = grid(5)
    rows = [make_row(x) for x in t if x != t[2]]
    assert find_gaps(rows, T0, T0 + 5 * INTERVAL_MS) == [t[2]]


def test_find_gaps_complete_grid():
    rows = [make_row(x) for x in grid(5)]
    assert find_gaps(rows, T0, T0 + 5 * INTERVAL_MS) == []


def test_count_zero_volume():
    t = grid(3)
    rows = [make_row(t[0]), make_row(t[1], volume="0.00000000"), make_row(t[2])]
    assert count_zero_volume(rows) == 1


def test_to_utc_str():
    assert to_utc_str(1609459200000) == "2021-01-01T00:00:00Z"
    assert to_utc_str(1788206400000) == "2026-08-31T20:00:00Z"


def test_write_clean_roundtrip(tmp_path):
    path = tmp_path / "sub" / "clean.csv"
    rows = [make_row(x) for x in grid(2)]
    write_clean(rows, path)

    data = path.read_bytes()
    assert b"\r\n" not in data
    lines = data.decode("utf-8").split("\n")
    assert lines[0] == "open_time,datetime_utc,open,high,low,close,volume"
    assert lines[1] == (
        "1609459200000,2021-01-01T00:00:00Z,29000.01000000,29500.50000000,"
        "28800.00000000,29400.12000000,1234.56789000"
    )
    assert lines[2].split(",")[2:] == list(rows[1][1:])
