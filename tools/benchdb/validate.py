"""Validate data/database.json against the data contract (DATA-CONTRACT.md).

Stdlib only. Exit code 0 when the database is valid, 1 with one line per
problem otherwise. Every rule here is named in DATA-CONTRACT.md; a new
class of source or a new unit extends the contract first and this file second.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

UNITS = {"percent", "score", "elo", "usd", "fraction"}
EVIDENCE_TYPES = {"official_publication_checked", "independent_publication_checked"}
REVIEW_STATUSES = {"source_checked"}
OBS_STATUSES = {"active", "superseded", "withdrawn"}
COMPARISON_SCOPES = {"publisher_comparison", "independent_measurement"}
COMPARISON_KINDS = {"official_release_comparison", "model_card", "official_blog"}
PRICE_KIND = "official_price_list"
# An evaluator that runs every model itself under one setup. It carries a cost
# per task, and a score only for a test a publisher's own page also printed, so
# an evaluator never adds a test of its own (COVERAGE.md).
INDEPENDENT_KIND = "independent_leaderboard"
PUBLICATION_KINDS = COMPARISON_KINDS | {PRICE_KIND, INDEPENDENT_KIND}
DISPLAY_GROUPS = {"price"}
PRICE_COMPONENTS = {
    "input",
    "cached_input",
    "cache_write",
    "cache_write_5m",
    "cache_write_1h",
    "output",
    "storage",
    "generation",
}
PRICE_UNITS = {
    "usd_per_million_tokens",
    "usd_per_million_tokens_per_hour",
    "usd_per_image",
    "usd_per_second",
    "usd_per_minute",
    "usd_per_video",
    "usd_per_million_chars",
    "usd_per_thousand_pages",
    "cny_per_million_tokens",
}
PRICE_SCHEDULES = {
    "standard",
    "batch",
    "fast",
    "flex",
    "ultrafast",
    "peak",
    "off_peak",
    "priority",
    "contributor",
    "free",
}
PRICE_BANDS = {"short", "long", "any"}
PRICE_MODALITIES = {"text", "image", "video"}
PRICE_OFFERS = {"list", "promotional"}
# Model facts (schema 1.2.0): what the developer prints about a model, each
# fact with the page it was read on. The kind says how its value is checked.
FACT_KINDS = {
    "context_window_tokens": "tokens",
    "max_output_tokens": "tokens",
    "input_modalities": "modalities",
    "output_modalities": "modalities",
    "weights": "weights",
    "license": "text",
}
FACT_KEYS = {"value", "as_printed", "source_url", "source_locator", "checked_on", "notes"}
MODALITIES = {"text", "image", "audio", "video", "pdf"}
WEIGHTS = {"open", "closed"}
# A Hugging Face licence id or a repo's own license_name (apache-2.0, glm-5.3)
# is an id; the value is the name a reader can look up.
LICENCE_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9.\-]*$")
# Active rows that share this key are the same price printed twice.
PRICE_KEY = (
    "model_id",
    "publication_id",
    "component",
    "schedule",
    "context_band",
    "region",
    "modality",
    "offer",
    "meter",
    "valid_from",
    "valid_until",
)
CONDITION_KEYS = {
    "model_label_as_published",
    "benchmark_label_as_published",
    "setup_as_reported",
    "model_setup_as_reported",
    "reasoning_effort",
    "harness",
    "tools",
    "fallback_policy",
    "attempt_budget",
    "context_tokens",
    "dataset_revision",
    "protocol_equivalence",
}
# Conditions that make two observations of one (benchmark, model, publication)
# legitimately distinct: the same row published at two efforts or two harnesses.
DISTINGUISHING = ("reasoning_effort", "harness", "tools", "fallback_policy", "attempt_budget", "context_tokens", "dataset_revision", "model_setup_as_reported")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATA_VERSION_RE = re.compile(r"^\d{8}\d{2}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
URL_RE = re.compile(r"^https://")
ABOUT_STATUSES = {"checked", "unverified", "pending"}
FORBIDDEN_CHARS = {"—": "em dash", "–": "en dash"}
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


def is_cost_per_task(b: dict) -> bool:
    return b.get("unit") == "usd" and b.get("unit_denominator") == "task" and b.get("higher_is_better") is False


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _walk_strings(node, prefix=""):
    if isinstance(node, str):
        yield prefix, node
    elif isinstance(node, dict):
        for key, value in node.items():
            yield from _walk_strings(value, f"{prefix}.{key}" if prefix else key)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk_strings(value, f"{prefix}[{index}]")


def check_facts(facts, as_of: str) -> list[str]:
    """Problems with one model's facts object; empty when it follows the contract."""
    if not isinstance(facts, dict):
        return ["facts must be an object"]
    out = []
    for name, fact in facts.items():
        kind = FACT_KINDS.get(name)
        if kind is None:
            out.append(f"facts: unknown fact {name!r}")
            continue
        if fact is None:
            continue
        if not isinstance(fact, dict):
            out.append(f"facts.{name}: must be an object or null")
            continue
        for key in sorted(set(fact) - FACT_KEYS):
            out.append(f"facts.{name}: unknown key {key!r}")
        if not URL_RE.match(str(fact.get("source_url", ""))):
            out.append(f"facts.{name}: source_url must be https")
        checked = str(fact.get("checked_on", ""))
        if not DATE_RE.match(checked):
            out.append(f"facts.{name}: checked_on must be YYYY-MM-DD")
        elif checked > as_of:
            out.append(f"facts.{name}: checked_on is after as_of")
        if not fact.get("as_printed"):
            out.append(f"facts.{name}: missing as_printed")
        value = fact.get("value")
        if kind == "tokens":
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                out.append(f"facts.{name}: value must be a positive whole number of tokens")
        elif kind == "modalities":
            if not isinstance(value, list) or not value or len(set(value)) != len(value) or not set(value) <= MODALITIES:
                out.append(f"facts.{name}: value must be a list of distinct entries from {sorted(MODALITIES)}")
        elif kind == "weights":
            if value not in WEIGHTS:
                out.append(f"facts.{name}: value must be one of {sorted(WEIGHTS)}")
        elif not isinstance(value, str) or not value.strip():
            out.append(f"facts.{name}: value must be text")
        elif name == "license" and LICENCE_SLUG_RE.match(value):
            out.append(f"facts.license: {value!r} is a repo id, not a licence name; write the name or drop the licence")
    # A licence is the terms the published weights come under; a model whose
    # weights are not published has none to print.
    if facts.get("license") is not None:
        weights = (facts.get("weights") or {}).get("value")
        if weights != "open":
            out.append("facts.license: only open weights carry a licence; set weights to open or drop the licence")
    return out


def validate(db: dict) -> list[str]:
    problems: list[str] = []
    err = problems.append

    # ---- top level -------------------------------------------------------
    for key in ("schema_version", "data_version", "as_of", "comparison_policy", "categories", "families", "benchmarks", "models", "publications", "observations", "change_log"):
        if key not in db:
            err(f"top: missing key {key}")
    if problems:
        return problems
    if not DATA_VERSION_RE.match(str(db["data_version"])):
        err(f"top: data_version must look like YYYYMMDDNN, got {db['data_version']!r}")
    if not DATE_RE.match(str(db["as_of"])):
        err(f"top: as_of must be YYYY-MM-DD, got {db['as_of']!r}")
    if db.get("default_publication_id") and db["default_publication_id"] not in {p.get("id") for p in db["publications"]}:
        err(f"top: default_publication_id {db['default_publication_id']!r} is not a publication")
    if str(db.get("schema_version", "")) >= "1.1.0" and "prices" not in db:
        err("top: schema 1.1.0 and later require a prices list (it may be empty)")
    if "prices" in db and not isinstance(db["prices"], list):
        err("top: prices must be a list")

    # ---- text hygiene (the whole score file, including a leftover draft key) ---
    for where, text in _walk_strings(db):
        for char, name in FORBIDDEN_CHARS.items():
            if char in text:
                err(f"text: {name} in {where}")
        if EMOJI_RE.search(text):
            err(f"text: emoji in {where}")

    # ---- categories ------------------------------------------------------
    cat_ids = Counter(c.get("id") for c in db["categories"])
    for cat_id, n in cat_ids.items():
        if n > 1:
            err(f"categories: duplicate id {cat_id}")
    orders = Counter(c.get("order") for c in db["categories"])
    for order, n in orders.items():
        if n > 1:
            err(f"categories: duplicate order {order}")
    for c in db["categories"]:
        for key in ("id", "name_en", "order", "description_en"):
            if not c.get(key) and c.get(key) != 0:
                err(f"categories[{c.get('id')}]: missing {key}")
        if c.get("id") and not ID_RE.match(c["id"]):
            err(f"categories: id {c['id']!r} is not kebab-case")

    # ---- families --------------------------------------------------------
    fam_ids = Counter(f.get("id") for f in db["families"])
    for fam_id, n in fam_ids.items():
        if n > 1:
            err(f"families: duplicate id {fam_id}")
    used_families = {b.get("family_id") for b in db["benchmarks"]}
    for f in db["families"]:
        if f.get("category_id") not in cat_ids:
            err(f"families[{f.get('id')}]: unknown category_id {f.get('category_id')!r}")
        if f.get("id") in used_families:
            about = f.get("about")
            if not isinstance(about, dict):
                err(f"families[{f.get('id')}]: a family with benchmarks needs an about block")
                continue
            if about.get("status") not in ABOUT_STATUSES:
                err(f"families[{f.get('id')}]: about.status must be one of {sorted(ABOUT_STATUSES)}")
            if about.get("status") != "pending" and not (about.get("what_it_tests") or "").strip():
                err(f"families[{f.get('id')}]: about.what_it_tests is required unless status is pending")
            for key in ("url", "evidence_url"):
                if about.get(key) and not URL_RE.match(about[key]):
                    err(f"families[{f.get('id')}]: about.{key} must be https")
            if about.get("introduced") is not None and not re.match(r"^\d{4}$", str(about["introduced"])):
                err(f"families[{f.get('id')}]: about.introduced must be a four digit year or null")

    # ---- benchmarks ------------------------------------------------------
    bench: dict[str, dict] = {}
    for b in db["benchmarks"]:
        bid = b.get("id")
        if bid in bench:
            err(f"benchmarks: duplicate id {bid}")
        bench[bid] = b
        if not bid or not ID_RE.match(bid):
            err(f"benchmarks: id {bid!r} is not kebab-case")
        if b.get("category_id") not in cat_ids:
            err(f"benchmarks[{bid}]: unknown category_id {b.get('category_id')!r}")
        if b.get("family_id") not in fam_ids:
            err(f"benchmarks[{bid}]: unknown family_id {b.get('family_id')!r}")
        if b.get("unit") not in UNITS:
            err(f"benchmarks[{bid}]: unit {b.get('unit')!r} not in {sorted(UNITS)}")
        if not isinstance(b.get("higher_is_better"), bool):
            err(f"benchmarks[{bid}]: higher_is_better must be a bool")
        if bid and bid.endswith("--" + str(b.get("unit"))) is False:
            err(f"benchmarks[{bid}]: id must end with --<unit>")
        if b.get("unit") == "usd" and not b.get("unit_denominator"):
            err(f"benchmarks[{bid}]: usd needs a unit_denominator (for example 'task')")
        for key in ("name", "version_label", "metric_label", "definition_status", "cross_publication_equivalence"):
            if not b.get(key):
                err(f"benchmarks[{bid}]: missing {key}")
        if b.get("display_group") is not None:
            if b["display_group"] not in DISPLAY_GROUPS:
                err(f"benchmarks[{bid}]: display_group {b['display_group']!r} not in {sorted(DISPLAY_GROUPS)}")
            elif not is_cost_per_task(b):
                err(f"benchmarks[{bid}]: display_group price is only for a usd cost per task")

    # ---- models ----------------------------------------------------------
    models: dict[str, dict] = {}
    for m in db["models"]:
        mid = m.get("id")
        if mid in models:
            err(f"models: duplicate id {mid}")
        models[mid] = m
        if not mid or not ID_RE.match(mid):
            err(f"models: id {mid!r} is not kebab-case")
        for key in ("name", "developer", "identity_scope"):
            if not m.get(key):
                err(f"models[{mid}]: missing {key}")
        if m.get("release_date") is not None and not DATE_RE.match(str(m["release_date"])):
            err(f"models[{mid}]: release_date must be YYYY-MM-DD or null")
        if not isinstance(m.get("latest", False), bool):
            err(f"models[{mid}]: latest must be true or false")
        # A result a publisher printed under another model's name keeps its own
        # identity: the id says so, and the name must say so too.
        if mid and "reported-as" in mid and "reported as" not in str(m.get("name", "")).lower():
            err(f"models[{mid}]: a reported-as identity must carry 'reported as' in its name")
        if "facts" in m:
            if str(db.get("schema_version", "")) < "1.2.0":
                err(f"models[{mid}]: facts need schema 1.2.0 or later")
            for line in check_facts(m["facts"], str(db["as_of"])):
                err(f"models[{mid}]: {line}")
    latest_by_dev: dict[str, list[str]] = defaultdict(list)
    for m in db["models"]:
        if m.get("latest") is True:
            latest_by_dev[m.get("developer")].append(m.get("id"))
    for dev, ids in latest_by_dev.items():
        if len(ids) > 1:
            err(f"models: {dev} has more than one latest model: {ids}")

    # ---- publications ----------------------------------------------------
    pubs: dict[str, dict] = {}
    for p in db["publications"]:
        pid = p.get("id")
        if pid in pubs:
            err(f"publications: duplicate id {pid}")
        pubs[pid] = p
        for key in ("name", "publisher", "url", "kind", "checked_on", "comparison_scope", "coverage"):
            if not p.get(key):
                err(f"publications[{pid}]: missing {key}")
        if p.get("url") and not URL_RE.match(p["url"]):
            err(f"publications[{pid}]: url must be https")
        kind = p.get("kind")
        if kind not in PUBLICATION_KINDS:
            err(f"publications[{pid}]: kind {kind!r} not in {sorted(PUBLICATION_KINDS)}")
        elif kind == PRICE_KIND and p.get("comparison_scope") != "price_list":
            err(f"publications[{pid}]: official_price_list must use comparison_scope price_list")
        elif kind in COMPARISON_KINDS and p.get("comparison_scope") != "publisher_comparison":
            err(f"publications[{pid}]: comparison_scope {p.get('comparison_scope')!r} must be publisher_comparison")
        elif kind == INDEPENDENT_KIND and p.get("comparison_scope") != "independent_measurement":
            err(f"publications[{pid}]: independent_leaderboard must use comparison_scope independent_measurement")
        if p.get("checked_on") and not DATE_RE.match(str(p["checked_on"])):
            err(f"publications[{pid}]: checked_on must be YYYY-MM-DD")
        if p.get("published_at") is not None and not DATE_RE.match(str(p["published_at"])):
            err(f"publications[{pid}]: published_at must be YYYY-MM-DD or null")

    # ---- observations ----------------------------------------------------
    obs_ids: set[str] = set()
    by_key: dict[tuple, list[dict]] = defaultdict(list)
    printed = {
        o.get("benchmark_id") for o in db["observations"]
        if o.get("status") == "active" and pubs.get(o.get("publication_id"), {}).get("kind") in COMPARISON_KINDS
    }
    for o in db["observations"]:
        oid = o.get("id")
        tag = f"observations[{oid}]"
        if oid in obs_ids:
            err(f"observations: duplicate id {oid}")
        obs_ids.add(oid)
        if not oid or not re.match(r"^obs-[0-9a-f]{20}$", str(oid)):
            err(f"{tag}: id must look like obs-<20 hex>")
        b = bench.get(o.get("benchmark_id"))
        if b is None:
            err(f"{tag}: unknown benchmark_id {o.get('benchmark_id')!r}")
        if o.get("model_id") not in models:
            err(f"{tag}: unknown model_id {o.get('model_id')!r}")
        if o.get("publication_id") not in pubs:
            err(f"{tag}: unknown publication_id {o.get('publication_id')!r}")
        elif pubs[o.get("publication_id")].get("kind") == PRICE_KIND:
            err(f"{tag}: observations cannot hang on a price list")
        else:
            independent = pubs[o.get("publication_id")].get("kind") == INDEPENDENT_KIND
            if independent and b is not None and not is_cost_per_task(b) and b.get("id") not in printed:
                err(f"{tag}: an independent leaderboard scores only a test a publisher's own page also printed")
            want = ("independent_publication_checked", "independent_measurement") if independent else ("official_publication_checked", "publisher_comparison")
            if (o.get("evidence_type"), o.get("comparison_scope")) != want:
                err(f"{tag}: evidence_type and comparison_scope must be {want[0]} and {want[1]} for this publication")
        value = o.get("value")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            err(f"{tag}: value must be a number, got {value!r}")
            value = None
        unit = o.get("unit")
        if unit not in UNITS:
            err(f"{tag}: unit {unit!r} not in {sorted(UNITS)}")
        if b is not None and unit != b.get("unit"):
            err(f"{tag}: unit {unit!r} differs from benchmark unit {b.get('unit')!r}")
        if b is not None and o.get("unit_denominator") != b.get("unit_denominator"):
            err(f"{tag}: unit_denominator differs from the benchmark's")
        if value is not None:
            if unit == "percent" and not 0 <= value <= 100:
                err(f"{tag}: percent out of range: {value}")
            if unit == "fraction" and not 0 <= value <= 1:
                err(f"{tag}: fraction out of range: {value}")
            if unit == "elo" and value <= 0:
                err(f"{tag}: elo must be a positive number: {value}")
            if unit == "usd" and value < 0:
                err(f"{tag}: usd must not be negative: {value}")
        cond = o.get("conditions")
        if not isinstance(cond, dict):
            err(f"{tag}: conditions must be an object")
            cond = {}
        unknown = set(cond) - CONDITION_KEYS
        if unknown:
            err(f"{tag}: unknown condition keys {sorted(unknown)}")
        for key in ("model_label_as_published", "benchmark_label_as_published", "setup_as_reported", "model_setup_as_reported", "protocol_equivalence"):
            if not cond.get(key):
                err(f"{tag}: conditions.{key} is required")
        if not o.get("source_url") or not URL_RE.match(str(o.get("source_url"))):
            err(f"{tag}: source_url must be https")
        if not o.get("source_locator"):
            err(f"{tag}: source_locator is required (where on the page the number is)")
        if not DATE_RE.match(str(o.get("checked_on"))):
            err(f"{tag}: checked_on must be YYYY-MM-DD")
        if o.get("evidence_type") not in EVIDENCE_TYPES:
            err(f"{tag}: evidence_type {o.get('evidence_type')!r} not in {sorted(EVIDENCE_TYPES)}")
        if o.get("review_status") not in REVIEW_STATUSES:
            err(f"{tag}: review_status {o.get('review_status')!r} unknown")
        if o.get("status") not in OBS_STATUSES:
            err(f"{tag}: status {o.get('status')!r} not in {sorted(OBS_STATUSES)}")
        if o.get("comparison_scope") not in COMPARISON_SCOPES:
            err(f"{tag}: comparison_scope {o.get('comparison_scope')!r} unknown")
        by_key[(o.get("benchmark_id"), o.get("model_id"), o.get("publication_id"))].append(o)

    for o in db["observations"]:
        sup = o.get("supersedes")
        if sup is not None and sup not in obs_ids:
            err(f"observations[{o.get('id')}]: supersedes unknown id {sup}")

    # Two active rows for one (benchmark, model, publication) must differ in a
    # distinguishing condition - Max beside Xhigh, never the same number twice.
    for key, rows in by_key.items():
        active = [r for r in rows if r.get("status") == "active"]
        if len(active) < 2:
            continue
        seen = set()
        for r in active:
            cond = r.get("conditions") or {}
            sig = tuple(cond.get(k) for k in DISTINGUISHING)
            if sig in seen:
                err(f"observations: {key} has two active rows with identical conditions; add reasoning_effort/harness, state the second configuration in model_setup_as_reported, or supersede one")
            seen.add(sig)

    # Two definitions of one family in the same unit whose shared models all
    # carry equal values are one test under two publisher labels: the label
    # belongs in benchmark_label_as_published, not in a second definition.
    values_by_bench: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for o in db["observations"]:
        if o.get("status") == "active" and isinstance(o.get("value"), (int, float)):
            values_by_bench[o.get("benchmark_id")][o.get("model_id")].add(o.get("value"))
    by_family: dict[str, list[dict]] = defaultdict(list)
    for b in db["benchmarks"]:
        by_family[b.get("family_id")].append(b)
    for fam, defs in by_family.items():
        for i, a in enumerate(defs):
            for b in defs[i + 1:]:
                if a.get("unit") != b.get("unit"):
                    continue
                va, vb = values_by_bench.get(a["id"], {}), values_by_bench.get(b["id"], {})
                shared = set(va) & set(vb)
                if len(shared) >= 2 and all(va[m] & vb[m] for m in shared):
                    err(f"benchmarks: {a['id']} and {b['id']} (family {fam}) carry equal values for all {len(shared)} shared models; one test under two labels, merge them and keep the label in benchmark_label_as_published")

    # ---- prices (official lists; never benchmark observations) -----------
    price_ids: set[str] = set()
    price_keys: dict[tuple, str] = {}
    for row in db.get("prices", []):
        pid = row.get("id")
        tag = f"prices[{pid}]"
        if pid in price_ids:
            err(f"prices: duplicate id {pid}")
        price_ids.add(pid)
        if not pid or not str(pid).startswith("price-") or not ID_RE.match(str(pid)):
            err(f"{tag}: id must be kebab-case and start with price-")
        mid = row.get("model_id")
        if mid not in models:
            err(f"{tag}: unknown model_id {mid!r}")
        pub_id = row.get("publication_id")
        pub = pubs.get(pub_id)
        if pub is None:
            err(f"{tag}: unknown publication_id {pub_id!r}")
        elif pub.get("kind") != PRICE_KIND:
            err(f"{tag}: publication {pub_id} is not an official_price_list")
        elif mid in models and pub.get("publisher") != models[mid].get("developer"):
            err(
                f"{tag}: publisher {pub.get('publisher')!r} is not the model developer "
                f"{models[mid].get('developer')!r}"
            )
        if row.get("component") not in PRICE_COMPONENTS:
            err(f"{tag}: component {row.get('component')!r} not in {sorted(PRICE_COMPONENTS)}")
        value = row.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            err(f"{tag}: value must be a number >= 0, got {value!r}")
        elif value < 0:
            err(f"{tag}: value must be >= 0, got {value}")
        if row.get("unit") not in PRICE_UNITS:
            err(f"{tag}: unit {row.get('unit')!r} not in {sorted(PRICE_UNITS)}")
        if row.get("schedule") not in PRICE_SCHEDULES:
            err(f"{tag}: schedule {row.get('schedule')!r} not in {sorted(PRICE_SCHEDULES)}")
        band = row.get("context_band")
        if band not in PRICE_BANDS:
            err(f"{tag}: context_band {band!r} not in {sorted(PRICE_BANDS)}")
        threshold = row.get("context_threshold_tokens")
        if band in {"short", "long"}:
            if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold <= 0:
                err(f"{tag}: short and long bands need a positive integer context_threshold_tokens")
        elif threshold is not None:
            err(f"{tag}: context_band any must leave context_threshold_tokens null")
        if row.get("modality") not in PRICE_MODALITIES:
            err(f"{tag}: modality {row.get('modality')!r} not in {sorted(PRICE_MODALITIES)}")
        if row.get("offer") not in PRICE_OFFERS:
            err(f"{tag}: offer {row.get('offer')!r} not in {sorted(PRICE_OFFERS)}")
        region = row.get("region")
        if region is not None and (not isinstance(region, str) or not region or not ID_RE.match(region)):
            err(f"{tag}: region must be null or kebab-case")
        meter = row.get("meter")
        if meter is not None and (not isinstance(meter, str) or not meter or not ID_RE.match(meter)):
            err(f"{tag}: meter must be null or kebab-case")
        for key in ("valid_from", "valid_until"):
            if row.get(key) is not None and not DATE_RE.match(str(row.get(key))):
                err(f"{tag}: {key} must be YYYY-MM-DD or null")
        if row.get("valid_from") and row.get("valid_until") and str(row["valid_from"]) > str(row["valid_until"]):
            err(f"{tag}: valid_from is after valid_until")
        if not DATE_RE.match(str(row.get("checked_on"))):
            err(f"{tag}: checked_on must be YYYY-MM-DD")
        if not row.get("source_url") or not URL_RE.match(str(row.get("source_url"))):
            err(f"{tag}: source_url must be https")
        if not row.get("source_locator"):
            err(f"{tag}: source_locator is required")
        if row.get("status") not in OBS_STATUSES:
            err(f"{tag}: status {row.get('status')!r} not in {sorted(OBS_STATUSES)}")
        if row.get("note") is not None and not isinstance(row.get("note"), str):
            err(f"{tag}: note must be a string or null")
        if row.get("status") == "active":
            sig = tuple(row.get(k) for k in PRICE_KEY)
            if sig in price_keys:
                err(f"{tag}: duplicate active price, same key as {price_keys[sig]}")
            else:
                price_keys[sig] = pid

    # ---- change log ------------------------------------------------------
    if not isinstance(db["change_log"], list) or not db["change_log"]:
        err("change_log: must be a non-empty list")
    else:
        for i, entry in enumerate(db["change_log"]):
            for key in ("at", "reviewer", "reason"):
                if not entry.get(key):
                    err(f"change_log[{i}]: missing {key}")
            if entry.get("at") and not DATE_RE.match(str(entry["at"])):
                err(f"change_log[{i}]: at must be YYYY-MM-DD")
        last = db["change_log"][-1].get("at")
        if last and str(db["as_of"]) < str(last):
            err("change_log: last entry is newer than as_of; bump as_of and data_version")

    return problems


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    path = Path(args[0]) if args else Path("data/database.json")
    try:
        db = load(path)
    except (OSError, ValueError) as exc:
        print(f"validate: cannot read {path}: {exc}")
        return 1
    problems = validate(db)
    for line in problems:
        print(line)
    counts = {k: len(db.get(k, [])) for k in ("categories", "benchmarks", "models", "publications", "observations", "prices")}
    if problems:
        print(f"validate: FAIL ({len(problems)} problems) {counts}")
        return 1
    print(f"validate: OK {counts} data_version={db['data_version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
