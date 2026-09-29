from backtester.download import (
    START,
    download_klines,
    parse_kline,
    to_ms,
    write_csv,
)

FOUR_HOURS_MS = 14400000


def make_kline(open_time):
    # Ligne au format Binance : 12 champs, prix et volumes en chaînes
    return [
        open_time, "29000.01000000", "29500.50000000", "28800.00000000",
        "29400.12000000", "1234.56789000", open_time + FOUR_HOURS_MS - 1,
        "36000000.12345678", 42000, "600.12345678", "17600000.87654321", "0",
    ]


def test_start_in_ms():
    assert to_ms(START) == 1609459200000


def test_parse_kline_keeps_six_fields_as_strings():
    row = make_kline(1609459200000)
    assert parse_kline(row) == (
        1609459200000, "29000.01000000", "29500.50000000",
        "28800.00000000", "29400.12000000", "1234.56789000",
    )


def test_download_klines_paginates():
    start = 1609459200000
    pages = [
        [make_kline(start + i * FOUR_HOURS_MS) for i in range(1000)],
        [make_kline(start + i * FOUR_HOURS_MS) for i in range(1000, 1500)],
    ]
    calls = []

    def fake_fetch_page(start_ms, end_ms, limit):
        calls.append(start_ms)
        return pages[len(calls) - 1]

    klines = download_klines(start, start + 10_000 * FOUR_HOURS_MS, fetch_page=fake_fetch_page)
    assert len(klines) == 1500
    assert len(calls) == 2
    assert calls[1] == pages[0][-1][0] + FOUR_HOURS_MS


def test_download_klines_excludes_end():
    start = 1609459200000
    end = start + 2 * FOUR_HOURS_MS
    page = [make_kline(start + i * FOUR_HOURS_MS) for i in range(3)]

    def fake_fetch_page(start_ms, end_ms, limit):
        return page

    klines = download_klines(start, end, fetch_page=fake_fetch_page)
    assert [k[0] for k in klines] == [start, start + FOUR_HOURS_MS]


def test_write_csv_is_deterministic(tmp_path):
    rows = [parse_kline(make_kline(1609459200000 + i * FOUR_HOURS_MS)) for i in range(3)]
    first = tmp_path / "a" / "first.csv"
    second = tmp_path / "b" / "second.csv"
    write_csv(rows, first)
    write_csv(rows, second)

    content = first.read_bytes()
    assert content == second.read_bytes()
    assert b"\r\n" not in content
    assert content.split(b"\n")[0] == b"open_time,open,high,low,close,volume"
