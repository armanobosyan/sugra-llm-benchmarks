"""Build the public payload public/benchmarks.v1.json from data/database.json,
and beside it public/benchmarks.v1.compact.json, the same records in the
smaller shape compact.py describes.

The payload is what the article loads. It carries the editorial taxonomy,
the benchmark definitions, the model identities, the publications and every
ACTIVE observation with its conditions and source. It copies those fields
only. A leftover key in the score file, including a pasted research draft,
stays out of the payload.

The output is deterministic (sorted keys, fixed separators, trailing newline)
so `build --check` can compare it byte for byte with the committed file.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from . import compact as compact_form
from .validate import load, validate

PAYLOAD_SCHEMA = "1.1.0"
# Observation fields copied into the payload. Nulls are dropped by compact().
OBS_FIELDS = (
    "id",
    "benchmark_id",
    "model_id",
    "publication_id",
    "value",
    "unit",
    "unit_denominator",
    "conditions",
    "source_url",
    "source_locator",
    "methodology_url",
    "checked_on",
    "evidence_type",
    "review_status",
    "comparison_scope",
)
FAMILY_FIELDS = ("id", "name", "category_id", "tags", "about")
# Price fields copied into the payload. Nulls are dropped by compact(), so a
# missing valid_until means the page stated no end date.
PRICE_FIELDS = (
    "id",
    "model_id",
    "publication_id",
    "component",
    "value",
    "unit",
    "schedule",
    "context_band",
    "context_threshold_tokens",
    "modality",
    "region",
    "meter",
    "offer",
    "valid_from",
    "valid_until",
    "checked_on",
    "source_url",
    "source_locator",
    "note",
)


def compact(node):
    """Drop null values and empty lists so the payload stays small."""
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            value = compact(value)
            if value is None or value == [] or value == {}:
                continue
            out[key] = value
        return out
    if isinstance(node, list):
        return [compact(v) for v in node]
    return node


def build_payload(db: dict, source_sha256: str) -> dict:
    active = [o for o in db["observations"] if o.get("status") == "active"]
    used_families = {b["family_id"] for b in db["benchmarks"]}
    families = [
        {k: f.get(k) for k in FAMILY_FIELDS}
        for f in db["families"]
        if f["id"] in used_families
    ]
    observations = [compact({k: o.get(k) for k in OBS_FIELDS}) for o in active]
    observations.sort(key=lambda o: o["id"])
    active_prices = [p for p in db.get("prices", []) if p.get("status") == "active"]
    prices = [compact({k: p.get(k) for k in PRICE_FIELDS}) for p in active_prices]
    prices.sort(key=lambda p: p["id"])
    payload = {
        "payload_schema": PAYLOAD_SCHEMA,
        "schema_version": db["schema_version"],
        "data_version": db["data_version"],
        "as_of": db["as_of"],
        "source_sha256": source_sha256,
        "default_publication_id": db.get("default_publication_id"),
        "comparison_policy": db["comparison_policy"],
        "taxonomy_note": db.get("taxonomy_note"),
        "categories": sorted(db["categories"], key=lambda c: c["order"]),
        "families": sorted(families, key=lambda f: f["id"]),
        "benchmarks": sorted(db["benchmarks"], key=lambda b: b["id"]),
        "models": sorted(db["models"], key=lambda m: m["id"]),
        "publications": sorted(db["publications"], key=lambda p: p["id"]),
        "observations": observations,
        "prices": prices,
        "change_log": db["change_log"],
        "counts": {
            "categories": len(db["categories"]),
            "benchmarks": len(db["benchmarks"]),
            "models": len(db["models"]),
            "publications": len(db["publications"]),
            "observations": len(observations),
            "prices": len(prices),
        },
    }
    return compact(payload)


def render(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def compact_path(out_path: Path) -> Path:
    """public/benchmarks.v1.json -> public/benchmarks.v1.compact.json"""
    return out_path.with_name(out_path.stem + ".compact" + out_path.suffix)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def no_loss_problems(previous: dict | None, db: dict) -> list[str]:
    """Every observation the committed payload carried must still exist in data.

    A row may be superseded or withdrawn (its status changes), but it may not
    vanish: the history of what a publisher printed is the point of the base.
    """
    if not previous:
        return []
    present = {o["id"] for o in db["observations"]}
    missing = sorted(o["id"] for o in previous.get("observations", []) if o["id"] not in present)
    problems = [f"build: observation {oid} was in the published payload and is gone from data" for oid in missing]
    price_ids = {p["id"] for p in db.get("prices", [])}
    gone_prices = sorted(p["id"] for p in previous.get("prices", []) if p["id"] not in price_ids)
    problems += [f"build: price {pid} was in the published payload and is gone from data" for pid in gone_prices]
    return problems


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    check = "--check" in args
    args = [a for a in args if a != "--check"]
    data_path = Path(args[0]) if args else Path("data/database.json")
    out_path = Path(args[1]) if len(args) > 1 else Path("public/benchmarks.v1.json")

    try:
        db = load(data_path)
    except (OSError, ValueError) as exc:
        print(f"build: cannot read {data_path}: {exc}")
        return 1
    problems = validate(db)
    previous = None
    if out_path.exists():
        try:
            previous = load(out_path)
        except (OSError, ValueError) as exc:
            problems.append(f"build: committed payload {out_path} is unreadable: {exc}")
    problems += no_loss_problems(previous, db)
    if problems:
        for line in problems:
            print(line)
        print(f"build: FAIL ({len(problems)} problems)")
        return 1

    payload = build_payload(db, sha256_of(data_path))
    outputs = [(out_path, render(payload)), (compact_path(out_path), render(compact_form.encode(payload)))]
    if check:
        stale = False
        for path, text in outputs:
            current = path.read_text(encoding="utf-8") if path.exists() else ""
            if current != text:
                print(f"build --check: {path} is stale; run `python -m tools.benchdb build` and commit the result")
                stale = True
            else:
                print(f"build --check: OK {path} matches {data_path} ({len(text)} bytes)")
        return 1 if stale else 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    for path, text in outputs:
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"build: wrote {path} ({len(text)} bytes, {db['data_version']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
