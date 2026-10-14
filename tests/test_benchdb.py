"""Tests for the validator and the payload build. Run: python -m unittest -v"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.benchdb import build, validate  # noqa: E402

DATA = ROOT / "data" / "database.json"


def fixture() -> dict:
    """A minimal valid database with the shapes the contract cares about."""
    return {
        "schema_version": "1.0.0",
        "data_version": "2026101401",
        "as_of": "2026-10-14",
        "default_publication_id": "publication-a",
        "comparison_policy": {"score_selection": "preserve every reported observation"},
        "categories": [{"id": "agentic-coding", "name_en": "Agentic coding", "order": 1, "description_en": "Changing real programs."}],
        "families": [{"id": "frontiercode", "name": "FrontierCode", "category_id": "agentic-coding", "tags": [], "about": {"maintainer": "Cognition", "url": "https://example.org/frontiercode", "what_it_tests": "Real repository tasks.", "introduced": "2026", "status": "checked", "evidence_url": None, "notes": None}}],
        "benchmarks": [
            {
                "id": "frontiercode-v1-1--percent",
                "family_id": "frontiercode",
                "category_id": "agentic-coding",
                "name": "FrontierCode v1.1",
                "version": "1.1",
                "version_label": "FrontierCode v1.1",
                "metric_label": "FrontierCode v1.1",
                "unit": "percent",
                "higher_is_better": True,
                "definition_status": "source_label_preserved",
                "cross_publication_equivalence": "not_established",
                "unit_denominator": None,
            },
            {
                "id": "cost-per-task--usd",
                "family_id": "frontiercode",
                "category_id": "agentic-coding",
                "name": "Cost per task",
                "version": None,
                "version_label": "Cost per task",
                "metric_label": "Average cost per task",
                "unit": "usd",
                "higher_is_better": False,
                "definition_status": "source_label_preserved",
                "cross_publication_equivalence": "not_established",
                "unit_denominator": "task",
            },
        ],
        "models": [
            {"id": "model-x", "name": "Model X", "developer": "Vendor A", "identity_scope": "named model", "release_date": None},
            {"id": "model-y-reported-as-x", "name": "Model Y (reported as Model X)", "developer": "Vendor A", "identity_scope": "named model", "release_date": None},
        ],
        "publications": [
            {
                "id": "publication-a",
                "name": "Model X launch",
                "publisher": "Vendor A",
                "url": "https://example.com/model-x",
                "source_id": "publication-a",
                "published_at": None,
                "checked_on": "2026-10-14",
                "kind": "official_release_comparison",
                "comparison_scope": "publisher_comparison",
                "methodology_url": None,
                "coverage": "Only the transcribed rows.",
            }
        ],
        "observations": [obs("obs-00000000000000000001", 46.2, "max"), obs("obs-00000000000000000002", 52.1, "xhigh")],
        "change_log": [{"at": "2026-10-14", "reviewer": "test", "reason": "seed", "added_observations": 2}],
        "research_catalog": {"policy": "never exported", "benchmark_registry": [{"name": "Imported — label kept as reported"}]},
    }


def obs(oid: str, value: float, effort: str | None, **over) -> dict:
    row = {
        "id": oid,
        "benchmark_id": "frontiercode-v1-1--percent",
        "model_id": "model-x",
        "publication_id": "publication-a",
        "value": value,
        "unit": "percent",
        "unit_denominator": None,
        "conditions": {
            "model_label_as_published": "Model X",
            "benchmark_label_as_published": "FrontierCode v1.1",
            "setup_as_reported": "as printed",
            "model_setup_as_reported": "as printed",
            "reasoning_effort": effort,
            "harness": None,
            "tools": None,
            "fallback_policy": None,
            "attempt_budget": None,
            "context_tokens": None,
            "dataset_revision": None,
            "protocol_equivalence": "not_established",
        },
        "source_url": "https://example.com/model-x",
        "source_locator": "Table 1",
        "methodology_url": None,
        "checked_on": "2026-10-14",
        "evidence_type": "official_publication_checked",
        "review_status": "source_checked",
        "status": "active",
        "comparison_scope": "publisher_comparison",
        "supersedes": None,
    }
    row.update(over)
    return row


class ValidateFixture(unittest.TestCase):
    def test_fixture_is_valid(self):
        self.assertEqual(validate.validate(fixture()), [])

    def test_two_efforts_are_two_rows(self):
        db = fixture()
        self.assertEqual(validate.validate(db), [])
        values = sorted(o["value"] for o in db["observations"])
        self.assertEqual(values, [46.2, 52.1])

    def test_same_conditions_twice_is_refused(self):
        db = fixture()
        db["observations"][1]["conditions"]["reasoning_effort"] = "max"
        problems = validate.validate(db)
        self.assertTrue(any("identical conditions" in p for p in problems), problems)

    def test_unit_must_match_benchmark(self):
        db = fixture()
        db["observations"][0]["unit"] = "score"
        problems = validate.validate(db)
        self.assertTrue(any("differs from benchmark unit" in p for p in problems), problems)

    def test_percent_range(self):
        db = fixture()
        db["observations"][0]["value"] = 101
        self.assertTrue(any("percent out of range" in p for p in validate.validate(db)))

    def test_elo_is_a_positive_integer(self):
        db = fixture()
        db["benchmarks"][0]["unit"] = "elo"
        db["benchmarks"][0]["id"] = "arena--elo"
        for o in db["observations"]:
            o["benchmark_id"] = "arena--elo"
            o["unit"] = "elo"
        db["observations"][0]["value"] = 1846
        db["observations"][1]["value"] = 18.5
        problems = validate.validate(db)
        self.assertEqual(len([p for p in problems if "elo must be" in p]), 1, problems)

    def test_usd_needs_denominator(self):
        db = fixture()
        db["benchmarks"][1]["unit_denominator"] = None
        self.assertTrue(any("usd needs a unit_denominator" in p for p in validate.validate(db)))

    def test_unknown_references_are_named(self):
        db = fixture()
        db["observations"][0]["model_id"] = "ghost"
        db["observations"][0]["publication_id"] = "nowhere"
        problems = validate.validate(db)
        self.assertTrue(any("unknown model_id 'ghost'" in p for p in problems), problems)
        self.assertTrue(any("unknown publication_id 'nowhere'" in p for p in problems), problems)

    def test_reported_as_identity_says_so_in_its_name(self):
        db = fixture()
        db["models"][1]["name"] = "Model Y"
        self.assertTrue(any("reported as" in p for p in validate.validate(db)))

    def test_used_family_needs_an_about_block(self):
        db = fixture()
        del db["families"][0]["about"]
        self.assertTrue(any("about block" in p for p in validate.validate(db)))

    def test_pending_about_passes_without_text(self):
        db = fixture()
        db["families"][0]["about"] = {"status": "pending"}
        self.assertEqual(validate.validate(db), [])

    def test_checked_about_needs_text_and_https(self):
        db = fixture()
        db["families"][0]["about"]["what_it_tests"] = ""
        self.assertTrue(any("what_it_tests" in p for p in validate.validate(db)))
        db = fixture()
        db["families"][0]["about"]["url"] = "http://example.org"
        self.assertTrue(any("must be https" in p for p in validate.validate(db)))

    def test_category_needs_an_english_description(self):
        db = fixture()
        del db["categories"][0]["description_en"]
        self.assertTrue(any("description_en" in p for p in validate.validate(db)))

    def test_em_dash_outside_the_catalog_is_refused(self):
        db = fixture()
        self.assertEqual(validate.validate(db), [], "catalog labels are kept as reported")
        db["observations"][0]["source_locator"] = "Table 1 — row 2"
        self.assertTrue(any("em dash" in p for p in validate.validate(db)))

    def test_supersedes_must_resolve(self):
        db = fixture()
        db["observations"][0]["supersedes"] = "obs-ffffffffffffffffffff"
        self.assertTrue(any("supersedes unknown id" in p for p in validate.validate(db)))

    def test_change_log_newer_than_as_of(self):
        db = fixture()
        db["change_log"].append({"at": "2026-11-01", "reviewer": "t", "reason": "r"})
        self.assertTrue(any("newer than as_of" in p for p in validate.validate(db)))


class BuildFixture(unittest.TestCase):
    def test_payload_drops_catalog_and_nulls(self):
        payload = build.build_payload(fixture(), "abc")
        self.assertNotIn("research_catalog", payload)
        row = payload["observations"][0]
        self.assertNotIn("supersedes", row)
        self.assertNotIn("harness", row["conditions"])
        self.assertEqual(row["conditions"]["reasoning_effort"], "max")
        self.assertEqual(payload["counts"]["observations"], 2)
        self.assertEqual(payload["source_sha256"], "abc")

    def test_payload_keeps_only_active_rows(self):
        db = fixture()
        db["observations"][1]["status"] = "withdrawn"
        payload = build.build_payload(db, "x")
        self.assertEqual([o["id"] for o in payload["observations"]], ["obs-00000000000000000001"])

    def test_render_is_deterministic(self):
        a = build.render(build.build_payload(fixture(), "x"))
        b = build.render(build.build_payload(copy.deepcopy(fixture()), "x"))
        self.assertEqual(a, b)
        self.assertTrue(a.endswith("\n"))

    def test_no_loss_against_previous_payload(self):
        db = fixture()
        previous = build.build_payload(db, "x")
        del db["observations"][1]
        problems = build.no_loss_problems(previous, db)
        self.assertEqual(len(problems), 1)
        self.assertIn("obs-00000000000000000002", problems[0])

    def test_withdrawn_row_is_not_a_loss(self):
        db = fixture()
        previous = build.build_payload(db, "x")
        db["observations"][1]["status"] = "withdrawn"
        self.assertEqual(build.no_loss_problems(previous, db), [])

    def test_check_detects_stale_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "database.json"
            out = Path(tmp) / "benchmarks.v1.json"
            data.write_text(json.dumps(fixture()), encoding="utf-8")
            self.assertEqual(build.main([str(data), str(out)]), 0)
            self.assertEqual(build.main(["--check", str(data), str(out)]), 0)
            db = fixture()
            db["data_version"] = "2026101501"
            data.write_text(json.dumps(db), encoding="utf-8")
            self.assertEqual(build.main(["--check", str(data), str(out)]), 1)


@unittest.skipUnless(DATA.exists(), "no data/database.json")
class RealDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = validate.load(DATA)

    def test_database_is_valid(self):
        self.assertEqual(validate.validate(self.db), [])

    def test_seed_counts_never_shrink(self):
        self.assertGreaterEqual(len(self.db["observations"]), 596)
        self.assertGreaterEqual(len(self.db["publications"]), 7)
        self.assertGreaterEqual(len(self.db["models"]), 21)

    def test_google_rows_from_the_launch_table(self):
        rows = {
            (o["benchmark_id"], o["model_id"]): o["value"]
            for o in self.db["observations"]
            if o["publication_id"] == "publication-google-gemini-4-argon"
        }
        for bench in ("deepswe-v1-1--percent", "frontierswe-v2--percent", "vibe-code-bench--percent", "terminal-bench-4-0--percent", "labbench-2--percent", "riemannbench--percent"):
            self.assertIn((bench, "gemini-4-argon"), rows, bench)

    def test_astra_terminal_bench_is_kept_per_publication(self):
        rows = [
            (o["publication_id"], o["value"])
            for o in self.db["observations"]
            if o["model_id"] == "gpt-6-astra" and o["benchmark_id"] == "terminal-bench-4-0--percent"
        ]
        values = sorted(v for _, v in rows)
        self.assertIn(58.2, values)
        self.assertIn(57.9, values)

    def test_sonnet_frontiercode_max_and_xhigh(self):
        rows = {
            o["conditions"]["reasoning_effort"]: o["value"]
            for o in self.db["observations"]
            if o["model_id"] == "claude-sonnet-5-5" and o["benchmark_id"] == "frontiercode-v1-1-main--percent"
        }
        self.assertEqual(rows, {"max": 46.2, "xhigh": 52.1})

    def test_payload_matches_committed_file(self):
        out = ROOT / "public" / "benchmarks.v1.json"
        self.assertTrue(out.exists(), "run python -m tools.benchdb build")
        text = build.render(build.build_payload(self.db, build.sha256_of(DATA)))
        self.assertEqual(out.read_text(encoding="utf-8"), text)


if __name__ == "__main__":
    unittest.main()
