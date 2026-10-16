"""The compact payload public/benchmarks.v1.compact.json: the same records as
public/benchmarks.v1.json in a smaller shape.

The full payload repeats the same long strings thousands of times: the setup
text a page printed under a table, the page URL, the locator. The compact
payload writes each distinct string once, in `strings`, and writes every
observation and price as a positional row of indexes into that table. Nothing
is dropped: decode(encode(payload)) is the full payload again, field for field.

Layout, all generated:

    encoding              "columns"
    strings               [s1, s2, ...]           a text cell is its 1-based index; 0 means absent
    observation_columns   ["id", "benchmark_id", ..., "conditions"]
    condition_columns     ["benchmark_label_as_published", ...]
    price_columns         ["id", "model_id", ...]
    observations          [[row], ...]            conditions is a nested row
    prices                [[row], ...]

A number cell (a value, a token threshold, a context length a page gave as a
number) is written as a one-element list, [93.4], so it is never read as an
index. A row drops its trailing absent cells. Every other top-level field of the full
payload is copied as it is.
"""

from __future__ import annotations

from collections import Counter

COMPACT_ENCODING = "columns"
ROW_SECTIONS = ("observations", "prices")


def _columns(rows: list[dict], nested: str | None = None) -> list[str]:
    seen: dict[str, None] = {}
    for row in rows:
        for key in row:
            if key != nested:
                seen.setdefault(key, None)
    cols = sorted(seen)
    if nested is not None:
        cols.append(nested)
    return cols


def _check_cell(column: str, value) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"compact: {column} holds {type(value).__name__}, only strings and numbers are encoded")


def _trim(row: list) -> list:
    while row and row[-1] == 0:
        row.pop()
    return row


def encode(payload: dict) -> dict:
    """The compact form of a full payload (the output of build.build_payload)."""
    observations = payload.get("observations", [])
    prices = payload.get("prices", [])
    obs_cols = _columns(observations, nested="conditions")
    cond_cols = _columns([o.get("conditions", {}) for o in observations])
    price_cols = _columns(prices)

    counts: Counter = Counter()

    def count(rows, cols, nested_cols=None):
        for row in rows:
            for col in cols:
                value = row.get(col)
                if value is None:
                    continue
                if col == "conditions":
                    count([value], nested_cols)
                    continue
                _check_cell(col, value)
                if isinstance(value, str):
                    counts[value] += 1

    count(observations, obs_cols, cond_cols)
    count(prices, price_cols)
    strings = [s for s, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]
    index = {s: i + 1 for i, s in enumerate(strings)}

    def cell(value):
        if value is None:
            return 0
        return [value] if isinstance(value, (int, float)) else index[value]

    def encode_row(row, cols, nested_cols=None):
        out = []
        for col in cols:
            value = row.get(col)
            if col == "conditions":
                out.append(_trim([cell(value.get(c)) for c in nested_cols]) if value else 0)
            else:
                out.append(cell(value))
        return _trim(out)

    compact = {k: v for k, v in payload.items() if k not in ROW_SECTIONS}
    compact["encoding"] = COMPACT_ENCODING
    compact["strings"] = strings
    compact["observation_columns"] = obs_cols
    compact["condition_columns"] = cond_cols
    compact["price_columns"] = price_cols
    # A section the full payload does not carry (an empty prices list is
    # dropped there) stays absent here too, so the round trip is exact.
    if "observations" in payload:
        compact["observations"] = [encode_row(o, obs_cols, cond_cols) for o in observations]
    if "prices" in payload:
        compact["prices"] = [encode_row(p, price_cols) for p in prices]
    return compact


def decode(compact: dict) -> dict:
    """The full payload again. The reference for the article's own decoder."""
    if compact.get("encoding") != COMPACT_ENCODING:
        raise ValueError(f"compact: unknown encoding {compact.get('encoding')!r}")
    strings = compact["strings"]

    def cell(value):
        if value == 0:
            return None
        if isinstance(value, list):
            return value[0]
        return strings[value - 1]

    def decode_row(row, cols, nested_cols=None):
        out = {}
        for i, col in enumerate(cols):
            value = row[i] if i < len(row) else 0
            if col == "conditions":
                if value != 0:
                    out[col] = decode_row(value, nested_cols)
                continue
            value = cell(value)
            if value is not None:
                out[col] = value
        return out

    obs_cols = compact["observation_columns"]
    cond_cols = compact["condition_columns"]
    price_cols = compact["price_columns"]
    payload = {
        k: v for k, v in compact.items()
        if k not in ("encoding", "strings", "observation_columns", "condition_columns", "price_columns", *ROW_SECTIONS)
    }
    if "observations" in compact:
        payload["observations"] = [decode_row(r, obs_cols, cond_cols) for r in compact["observations"]]
    if "prices" in compact:
        payload["prices"] = [decode_row(r, price_cols) for r in compact["prices"]]
    return payload
