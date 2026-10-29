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

from tools.benchdb import build, compact, validate  # noqa: E402

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
        "research_catalog": {"policy": "never exported", "benchmark_registry": [{"name": "Imported label kept as reported"}]},
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

    def test_second_configuration_in_the_same_cell_is_a_row(self):
        db = fixture()
        db["observations"][1]["conditions"]["reasoning_effort"] = "max"
        db["observations"][1]["conditions"]["model_setup_as_reported"] = 'second value printed in the same cell as "60.9% (Mythos 5.1)"'
        self.assertEqual(validate.validate(db), [])

    def test_same_values_under_two_labels_is_refused(self):
        db = fixture()
        db["benchmarks"].append({**db["benchmarks"][0], "id": "frontiercode-v1-1-main--percent", "name": "FrontierCode v1.1 (main)"})
        db["observations"] += [
            obs("obs-00000000000000000003", 46.2, "max", benchmark_id="frontiercode-v1-1-main--percent"),
            obs("obs-00000000000000000004", 30.0, None, model_id="model-y-reported-as-x"),
            obs("obs-00000000000000000005", 30.0, None, model_id="model-y-reported-as-x", benchmark_id="frontiercode-v1-1-main--percent"),
        ]
        problems = validate.validate(db)
        self.assertTrue(any("one test under two labels" in p for p in problems), problems)

    def test_different_values_under_two_labels_are_two_definitions(self):
        db = fixture()
        db["benchmarks"].append({**db["benchmarks"][0], "id": "frontiercode-v1-1-main--percent", "name": "FrontierCode v1.1 (main)"})
        db["observations"] += [
            obs("obs-00000000000000000003", 41.0, "max", benchmark_id="frontiercode-v1-1-main--percent"),
            obs("obs-00000000000000000004", 30.0, None, model_id="model-y-reported-as-x"),
            obs("obs-00000000000000000005", 30.0, None, model_id="model-y-reported-as-x", benchmark_id="frontiercode-v1-1-main--percent"),
        ]
        self.assertEqual(validate.validate(db), [])

    def test_unit_must_match_benchmark(self):
        db = fixture()
        db["observations"][0]["unit"] = "score"
        problems = validate.validate(db)
        self.assertTrue(any("differs from benchmark unit" in p for p in problems), problems)

    def test_percent_range(self):
        db = fixture()
        db["observations"][0]["value"] = 101
        self.assertTrue(any("percent out of range" in p for p in validate.validate(db)))

    def test_elo_is_a_positive_number(self):
        db = fixture()
        db["benchmarks"][0]["unit"] = "elo"
        db["benchmarks"][0]["id"] = "arena--elo"
        for o in db["observations"]:
            o["benchmark_id"] = "arena--elo"
            o["unit"] = "elo"
        db["observations"][0]["value"] = 1747.8
        db["observations"][1]["value"] = 0
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

    def test_em_dash_in_the_score_file_is_refused(self):
        db = fixture()
        self.assertEqual(validate.validate(db), [])
        db["observations"][0]["source_locator"] = "Table 1 — row 2"
        self.assertTrue(any("em dash" in p for p in validate.validate(db)))
        db = fixture()
        db["research_catalog"]["policy"] = "never — exported"
        self.assertTrue(any("em dash" in p for p in validate.validate(db)))

    def test_supersedes_must_resolve(self):
        db = fixture()
        db["observations"][0]["supersedes"] = "obs-ffffffffffffffffffff"
        self.assertTrue(any("supersedes unknown id" in p for p in validate.validate(db)))

    def test_change_log_newer_than_as_of(self):
        db = fixture()
        db["change_log"].append({"at": "2026-11-01", "reviewer": "t", "reason": "r"})
        self.assertTrue(any("newer than as_of" in p for p in validate.validate(db)))

    def test_prices_are_optional_on_a_1_0_database(self):
        self.assertEqual(validate.validate(fixture()), [])

    def test_price_publisher_must_be_the_model_developer(self):
        db = fixture()
        db["publications"].append(
            {
                "id": "publication-prices",
                "name": "Vendor A prices",
                "publisher": "Vendor B",
                "url": "https://example.com/prices",
                "source_id": "publication-prices",
                "published_at": None,
                "checked_on": "2026-10-15",
                "kind": "official_price_list",
                "comparison_scope": "price_list",
                "methodology_url": None,
                "coverage": "The token table only.",
            }
        )
        db["prices"] = [
            {
                "id": "price-model-x-input-standard-any-list",
                "model_id": "model-x",
                "publication_id": "publication-prices",
                "component": "input",
                "value": 2,
                "unit": "usd_per_million_tokens",
                "schedule": "standard",
                "context_band": "any",
                "context_threshold_tokens": None,
                "modality": "text",
                "region": None,
                "meter": None,
                "offer": "list",
                "valid_from": None,
                "valid_until": None,
                "checked_on": "2026-10-15",
                "source_url": "https://example.com/prices",
                "source_locator": "Standard table",
                "status": "active",
                "note": None,
            }
        ]
        problems = validate.validate(db)
        self.assertTrue(any("not the model developer" in p for p in problems), problems)
        db["publications"][-1]["publisher"] = "Vendor A"
        self.assertEqual(validate.validate(db), [])

    def test_observation_cannot_hang_on_a_price_list(self):
        db = fixture()
        db["publications"].append(
            {
                "id": "publication-prices",
                "name": "Vendor A prices",
                "publisher": "Vendor A",
                "url": "https://example.com/prices",
                "source_id": "publication-prices",
                "published_at": None,
                "checked_on": "2026-10-15",
                "kind": "official_price_list",
                "comparison_scope": "price_list",
                "methodology_url": None,
                "coverage": "The token table only.",
            }
        )
        db["observations"][0]["publication_id"] = "publication-prices"
        self.assertTrue(any("cannot hang on a price list" in p for p in validate.validate(db)))

    def _independent(self, db: dict) -> dict:
        db["publications"].append(
            {
                "id": "publication-evaluator",
                "name": "Evaluator leaderboard",
                "publisher": "Evaluator",
                "url": "https://example.org/board",
                "source_id": "publication-evaluator",
                "published_at": None,
                "checked_on": "2026-10-27",
                "kind": "independent_leaderboard",
                "comparison_scope": "independent_measurement",
                "methodology_url": None,
                "coverage": "The cost column only.",
            }
        )
        row = obs(
            "obs-00000000000000000009", 6.0, None,
            benchmark_id="cost-per-task--usd", unit="usd", unit_denominator="task",
            publication_id="publication-evaluator",
            evidence_type="independent_publication_checked", comparison_scope="independent_measurement",
        )
        db["observations"].append(row)
        return row

    def test_independent_leaderboard_carries_a_cost_per_task(self):
        db = fixture()
        self._independent(db)
        db["benchmarks"][1]["display_group"] = "price"
        self.assertEqual(validate.validate(db), [])

    def test_independent_leaderboard_refuses_a_score(self):
        db = fixture()
        row = self._independent(db)
        row.update(benchmark_id="frontiercode-v1-1--percent", unit="percent", unit_denominator=None, value=50.0)
        self.assertTrue(any("carries only a usd cost per task" in p for p in validate.validate(db)))

    def test_independent_row_needs_its_own_evidence_type(self):
        db = fixture()
        row = self._independent(db)
        row.update(evidence_type="official_publication_checked", comparison_scope="publisher_comparison")
        self.assertTrue(any("must be independent_publication_checked" in p for p in validate.validate(db)))
        db = fixture()
        db["observations"][0].update(evidence_type="independent_publication_checked", comparison_scope="independent_measurement")
        self.assertTrue(any("must be official_publication_checked" in p for p in validate.validate(db)))

    def test_display_group_price_is_only_for_a_cost_per_task(self):
        db = fixture()
        db["benchmarks"][0]["display_group"] = "price"
        self.assertTrue(any("only for a usd cost per task" in p for p in validate.validate(db)))
        db = fixture()
        db["benchmarks"][1]["display_group"] = "top"
        self.assertTrue(any("display_group 'top'" in p for p in validate.validate(db)))

    def test_duplicate_active_price_is_refused(self):
        db = fixture()
        db["publications"].append(
            {
                "id": "publication-prices",
                "name": "Vendor A prices",
                "publisher": "Vendor A",
                "url": "https://example.com/prices",
                "source_id": "publication-prices",
                "published_at": None,
                "checked_on": "2026-10-15",
                "kind": "official_price_list",
                "comparison_scope": "price_list",
                "methodology_url": None,
                "coverage": "The token table only.",
            }
        )
        row = {
            "id": "price-model-x-input-standard-any-list",
            "model_id": "model-x",
            "publication_id": "publication-prices",
            "component": "input",
            "value": 2,
            "unit": "usd_per_million_tokens",
            "schedule": "standard",
            "context_band": "any",
            "context_threshold_tokens": None,
            "modality": "text",
            "region": None,
            "meter": None,
            "offer": "list",
            "valid_from": None,
            "valid_until": None,
            "checked_on": "2026-10-15",
            "source_url": "https://example.com/prices",
            "source_locator": "Standard table",
            "status": "active",
            "note": None,
        }
        other = dict(row)
        other["id"] = "price-model-x-input-standard-any-list-again"
        other["value"] = 3
        db["prices"] = [row, other]
        self.assertTrue(any("duplicate active price" in p for p in validate.validate(db)))


def fact(value, **over) -> dict:
    row = {"value": value, "as_printed": str(value), "source_url": "https://example.com/model-x", "source_locator": "Model card", "checked_on": "2026-10-14"}
    row.update(over)
    return row


class ModelFacts(unittest.TestCase):
    def with_facts(self, **facts) -> dict:
        db = fixture()
        db["schema_version"] = "1.2.0"
        db["prices"] = []
        db["models"][0]["facts"] = facts
        return db

    def problems(self, **facts) -> list[str]:
        return validate.validate(self.with_facts(**facts))

    def test_a_full_facts_object_is_valid(self):
        self.assertEqual(
            self.problems(
                context_window_tokens=fact(1048576, as_printed="1,048,576"),
                max_output_tokens=fact(65536),
                input_modalities=fact(["text", "image", "audio", "video", "pdf"]),
                output_modalities=fact(["text"]),
                weights=fact("open"),
                license=fact("Apache 2.0"),
            ),
            [],
        )

    def test_an_unprinted_fact_is_null(self):
        self.assertEqual(self.problems(context_window_tokens=None, weights=fact("closed")), [])

    def test_facts_need_schema_1_2(self):
        db = self.with_facts(weights=fact("closed"))
        db["schema_version"] = "1.1.0"
        self.assertTrue(any("facts need schema 1.2.0" in p for p in validate.validate(db)))

    def test_every_fact_needs_its_page_and_date(self):
        found = self.problems(weights=fact("closed", source_url="http://example.com"), max_output_tokens=fact(8192, checked_on="2026-10-15"))
        self.assertTrue(any("weights: source_url must be https" in p for p in found))
        self.assertTrue(any("max_output_tokens: checked_on is after as_of" in p for p in found))
        found = self.problems(weights=fact("closed", as_printed=""))
        self.assertTrue(any("weights: missing as_printed" in p for p in found))

    def test_token_counts_are_positive_whole_numbers(self):
        for bad in (0, -1, 1.5, "1M", True):
            found = self.problems(context_window_tokens=fact(bad))
            self.assertTrue(any("positive whole number" in p for p in found), bad)

    def test_modalities_come_from_the_list(self):
        for bad in ([], ["text", "text"], ["text", "smell"], "text"):
            found = self.problems(input_modalities=fact(bad))
            self.assertTrue(any("input_modalities: value must be a list" in p for p in found), bad)

    def test_weights_are_open_or_closed(self):
        self.assertTrue(any("weights: value must be one of" in p for p in self.problems(weights=fact("partly"))))

    def test_only_open_weights_carry_a_licence(self):
        self.assertTrue(any("only open weights carry a licence" in p for p in self.problems(weights=fact("closed"), license=fact("MIT"))))
        self.assertTrue(any("only open weights carry a licence" in p for p in self.problems(license=fact("MIT"))))

    def test_a_licence_is_a_name_not_a_repo_id(self):
        for slug in ("apache-2.0", "glm-5.3", "qwen3.8-max"):
            self.assertTrue(any("not a licence name" in p for p in self.problems(weights=fact("open"), license=fact(slug))), slug)
        for name in ("MIT", "Apache 2.0", "Kimi K3 License"):
            self.assertEqual(self.problems(weights=fact("open"), license=fact(name)), [], name)

    def test_unknown_facts_and_keys_are_refused(self):
        found = self.problems(speed=fact(90), weights=fact("closed", rank=1))
        self.assertTrue(any("unknown fact 'speed'" in p for p in found))
        self.assertTrue(any("weights: unknown key 'rank'" in p for p in found))

    def test_payload_keeps_the_facts_and_drops_null_ones(self):
        db = self.with_facts(context_window_tokens=None, weights=fact("closed"))
        payload = build.build_payload(db, "0" * 64)
        model = next(m for m in payload["models"] if m["id"] == "model-x")
        self.assertEqual(model["facts"], {"weights": fact("closed")})


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
            self.assertTrue((Path(tmp) / "benchmarks.v1.compact.json").exists())
            self.assertEqual(build.main(["--check", str(data), str(out)]), 0)
            db = fixture()
            db["data_version"] = "2026101501"
            data.write_text(json.dumps(db), encoding="utf-8")
            self.assertEqual(build.main(["--check", str(data), str(out)]), 1)

    def test_check_detects_stale_compact_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "database.json"
            out = Path(tmp) / "benchmarks.v1.json"
            data.write_text(json.dumps(fixture()), encoding="utf-8")
            self.assertEqual(build.main([str(data), str(out)]), 0)
            (Path(tmp) / "benchmarks.v1.compact.json").write_text("{}", encoding="utf-8")
            self.assertEqual(build.main(["--check", str(data), str(out)]), 1)


class CompactFixture(unittest.TestCase):
    def test_round_trip_is_exact(self):
        payload = build.build_payload(fixture(), "abc")
        small = compact.encode(payload)
        self.assertEqual(small["encoding"], "columns")
        self.assertEqual(compact.decode(small), payload)

    def test_strings_are_written_once_and_numbers_stay_numbers(self):
        payload = build.build_payload(fixture(), "abc")
        small = compact.encode(payload)
        self.assertEqual(len(small["strings"]), len(set(small["strings"])))
        value_col = small["observation_columns"].index("value")
        for row in small["observations"]:
            self.assertIsInstance(row[value_col], list)
            self.assertEqual(len(row[value_col]), 1)

    def test_absent_cells_are_zero_and_trailing_ones_are_dropped(self):
        payload = build.build_payload(fixture(), "abc")
        small = compact.encode(payload)
        cols = small["observation_columns"]
        for row in small["observations"]:
            self.assertLessEqual(len(row), len(cols))
            self.assertNotEqual(row[-1], 0)
        # a row without conditions decodes without the key
        bare = {"observations": [{"id": "obs-1", "value": 1}], "prices": []}
        self.assertEqual(compact.decode(compact.encode(bare)), bare)

    def test_mixed_types_in_one_column_round_trip(self):
        rows = {"observations": [
            {"id": "obs-1", "value": 1, "conditions": {"context_tokens": 128000}},
            {"id": "obs-2", "value": 2.5, "conditions": {"context_tokens": "up to 1M"}},
        ], "prices": [{"id": "price-1", "value": 0}]}
        self.assertEqual(compact.decode(compact.encode(rows)), rows)

    def test_refuses_a_cell_that_is_not_text_or_number(self):
        rows = {"observations": [{"id": "obs-1", "value": 1, "flag": True}], "prices": []}
        with self.assertRaises(ValueError):
            compact.encode(rows)
        rows = {"observations": [{"id": "obs-1", "value": 1, "tags": ["a"]}], "prices": []}
        with self.assertRaises(ValueError):
            compact.encode(rows)

    def test_render_is_deterministic(self):
        a = build.render(compact.encode(build.build_payload(fixture(), "x")))
        b = build.render(compact.encode(build.build_payload(copy.deepcopy(fixture()), "x")))
        self.assertEqual(a, b)


@unittest.skipUnless(DATA.exists(), "no data/database.json")
class RealDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = validate.load(DATA)

    def test_database_is_valid(self):
        self.assertEqual(validate.validate(self.db), [])

    def test_score_file_has_no_unverified_draft(self):
        self.assertNotIn("research_catalog", self.db)
        self.assertFalse((DATA.parent / "research-catalog.json").exists())

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

    def test_gemini_4_carbon_table_and_launch_post(self):
        def values(publication_id):
            return {
                (o["benchmark_id"], o["model_id"]): o["value"]
                for o in self.db["observations"]
                if o["publication_id"] == publication_id and o["status"] == "active"
            }

        table = values("publication-google-gemini-4-carbon")
        self.assertEqual(len(table), 80)
        self.assertEqual(table[("swe-sweep--percent", "gemini-4-carbon")], 9.6)
        self.assertEqual(table[("vending-bench-2--usd", "gemini-4-carbon")], 16484)
        self.assertEqual(table[("graphwalks-256k-1m-bfs-f1--percent", "claude-fable-5-1")], 65.0)
        self.assertNotIn(("exploitgym--percent", "claude-fable-5-1"), table)
        post = [o for o in self.db["observations"] if o["publication_id"] == "publication-google-gemini-4-carbon-blog"]
        self.assertEqual(len(post), 43)
        caps = sorted(
            o["conditions"]["attempt_budget"]
            for o in post
            if o["benchmark_id"] == "exploitgym--percent" and o["model_id"] == "gemini-4-carbon"
        )
        self.assertEqual(caps, ["time cap per task: 10h", "time cap per task: 6h"])
        argon = [o for o in self.db["observations"] if o["publication_id"] == "publication-google-gemini-4-argon"]
        self.assertTrue(all(o["source_url"] == "https://deepmind.google/models/model-cards/gemini-4-argon/" for o in argon))

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

    def test_benchmark_rows_do_not_hang_on_a_price_list(self):
        price_pubs = {p["id"] for p in self.db["publications"] if p.get("kind") == "official_price_list"}
        self.assertEqual(len(price_pubs), 16)
        self.assertTrue(all(o["publication_id"] not in price_pubs for o in self.db["observations"]))
        self.assertGreaterEqual(len(self.db["prices"]), 2480)

    def test_vals_cost_per_task_is_one_setup(self):
        rows = [o for o in self.db["observations"] if o["benchmark_id"] == "vibe-code-bench-1-1-cost-per-test--usd"]
        self.assertEqual(len(rows), 73)
        self.assertEqual(len({o["model_id"] for o in rows}), 73)
        self.assertEqual({o["conditions"]["harness"] for o in rows}, {"OpenHands"})
        self.assertEqual({o["publication_id"] for o in rows}, {"publication-vals-ai-vibe-code-bench-1-1"})
        value = {o["model_id"]: o["value"] for o in rows}
        self.assertEqual(value["gpt-6-1-terra"], 6.0)
        self.assertEqual(value["claude-sonnet-5-5"], 31.25)
        self.assertEqual(value["deepseek-v4-1-flash-1017"], 0.58)
        self.assertEqual(value["mistral-large-4"], 39.46)

    def test_official_price_spot_checks(self):
        active = [p for p in self.db["prices"] if p["status"] == "active"]

        def one(**query):
            hits = [p for p in active if all(p.get(k) == v for k, v in query.items())]
            self.assertEqual(len(hits), 1, query)
            return hits[0]

        self.assertEqual(one(model_id="gpt-6-astra", schedule="standard", context_band="short", component="input")["value"], 10)
        self.assertEqual(one(model_id="gpt-5-4", schedule="batch", context_band="short", component="cached_input")["value"], 0.13)
        self.assertEqual(one(model_id="claude-fable-5-1", schedule="standard", component="cached_input")["value"], 0.25)
        self.assertEqual(one(model_id="grok-4-7", schedule="fast", context_band="short", component="input")["value"], 4)
        self.assertEqual(one(model_id="gemini-4-argon", schedule="standard", component="input", offer="promotional", valid_until="2026-11-30")["value"], 2)
        self.assertEqual(one(model_id="gemini-3-8-flash", schedule="standard", component="storage", offer="promotional", valid_until="2026-12-31")["value"], 0.5)
        self.assertEqual(one(model_id="kimi-k3", component="input", publication_id="publication-moonshot-kimi-api-pricing")["unit"], "cny_per_million_tokens")
        self.assertEqual(one(model_id="kimi-k3", component="input", publication_id="publication-moonshot-kimi-api-pricing-international")["value"], 3)
        self.assertEqual(one(model_id="kimi-k3-1-pro", component="output", publication_id="publication-moonshot-kimi-api-pricing-international")["value"], 10)
        self.assertEqual(one(model_id="kimi-k3-1-pro-highspeed", component="output", publication_id="publication-moonshot-kimi-api-pricing")["value"], 136)
        self.assertEqual(one(model_id="minimax-m3", component="input", schedule="standard", context_band="long")["value"], 0.6)
        self.assertEqual(one(model_id="mimo-v2-6-pro", component="output", schedule="standard", region="international")["value"], 0.87)
        self.assertEqual(one(model_id="muse-wonder", component="output")["value"], 20)
        self.assertEqual(one(model_id="mai-thinking-1", component="output")["value"], 8)
        self.assertEqual(one(model_id="phi-4-reasoning-plus", component="input")["value"], 0.125)
        self.assertEqual(one(model_id="step-3-7-flash", component="cached_input")["value"], 0.04)
        self.assertEqual(one(model_id="mistral-small-4", component="input")["value"], 0.15)
        self.assertFalse({"mistral-small-2603", "mistral-large-2512", "ministral-14b-2512", "gemini-3-flash-preview"} & {m["id"] for m in self.db["models"]})
        self.assertEqual(one(model_id="glm-5-3", component="input")["value"], 1.4)
        self.assertEqual(one(model_id="gpt-6-1-terra", component="output", schedule="standard", context_band="short")["value"], 5)
        self.assertEqual(one(model_id="gpt-6-1-terra", component="input", schedule="fast", context_band="long")["value"], 4)
        self.assertEqual(one(model_id="qwen3-8-max", component="input", region="international")["value"], 2)
        self.assertEqual(one(model_id="mistral-large-4", component="input", offer="promotional")["value"], 0.68)
        self.assertIsNone(one(model_id="mistral-large-4", component="input", offer="promotional").get("valid_until"))
        latest = {m["developer"]: m["id"] for m in self.db["models"] if m.get("latest") is True}
        self.assertEqual(
            latest,
            {
                "Google": "gemini-4-carbon",
                "OpenAI": "gpt-6-astra",
                "Anthropic": "claude-fable-5-1",
                "Alibaba": "qwen3-8-max",
                "xAI": "grok-4-7",
                "Moonshot AI": "kimi-k3-1-pro",
                "DeepSeek": "deepseek-v4-1-flash-1017",
                "Z.ai": "glm-5-3",
                "MiniMax": "minimax-m3-1-flash",
            },
        )

    def test_publisher_pages_keep_printed_numbers(self):
        def one(publication_id, benchmark_id, model_id, **cond):
            hits = [
                o for o in self.db["observations"]
                if o["publication_id"] == publication_id
                and o["benchmark_id"] == benchmark_id
                and o["model_id"] == model_id
                and all(o["conditions"].get(k) == v for k, v in cond.items())
            ]
            self.assertEqual(len(hits), 1, (publication_id, benchmark_id, model_id, cond))
            return hits[0]["value"]

        self.assertEqual(one("publication-mistral-large-4", "deepswe-v1-1--percent", "mistral-large-4"), 61.7)
        self.assertEqual(one("publication-zai-glm-5-3", "terminal-bench-2-1--percent", "glm-5-3"), 88.2)
        self.assertEqual(one("publication-zai-glm-5-3", "cybergym--percent", "claude-fable-5"), 83.8)
        self.assertEqual(one("publication-deepseek-v4-1-flash", "gpqa-diamond--percent", "deepseek-v4-1-flash"), 90.9)
        self.assertEqual(one("publication-moonshot-kimi-k3", "gpqa-diamond--percent", "kimi-k3"), 93.5)
        self.assertEqual(one("publication-zai-glm-5-3-blog", "zai-code-bench--percent", "glm-5-3", reasoning_effort="Max"), 34.5)
        self.assertEqual(one("publication-zai-glm-5-3-blog", "zai-code-bench--percent", "claude-fable-5"), 39.5)
        muse = {m["id"]: m for m in self.db["models"] if m["id"] in ("muse-spark", "muse-spark-1-1")}
        self.assertEqual(muse["muse-spark-1-1"]["release_date"], "2026-07-09")
        self.assertIsNone(muse["muse-spark"]["release_date"])
        # No publisher printed a score for either; an independent cost per task may exist.
        self.assertTrue(all(o["model_id"] not in muse for o in self.db["observations"] if o["comparison_scope"] == "publisher_comparison"))

    def test_official_dates_match_the_page(self):
        models = {m["id"]: m for m in self.db["models"]}
        pubs = {p["id"]: p for p in self.db["publications"]}
        self.assertEqual(pubs["publication-anthropic-claude-opus-5-5"]["published_at"], "2026-09-22")
        self.assertEqual(models["claude-opus-5-5"]["release_date"], "2026-09-22")
        self.assertEqual(pubs["publication-anthropic-claude-sonnet-5-5"]["published_at"], "2026-09-28")
        self.assertEqual(models["claude-sonnet-5-5"]["release_date"], "2026-09-28")
        self.assertEqual(pubs["publication-xai-grok-4-7-model-card"]["published_at"], "2026-09-21")
        self.assertEqual(models["grok-4-7"]["release_date"], "2026-09-21")
        self.assertEqual(pubs["publication-openai-gpt-6-astra"]["published_at"], "2026-09-03")
        self.assertEqual(models["gpt-6-astra"]["release_date"], "2026-09-03")
        self.assertIsNone(pubs["publication-openai-gpt-6-1-sol"]["published_at"])
        self.assertEqual(models["gpt-6-1-sol"]["release_date"], "2026-09-29")
        self.assertIsNone(pubs["publication-deepseek-v4-pro-0813"]["published_at"])
        self.assertIsNone(models["deepseek-v4-pro-0813"]["release_date"])
        self.assertIsNone(pubs["publication-deepseek-v4-flash-0731"]["published_at"])
        self.assertIsNone(models["deepseek-v4-flash-0731"]["release_date"])
        self.assertIsNone(models["qwen3-8-27b"]["release_date"])
        self.assertEqual(models["glm-5-3"]["release_date"], "2026-08-18")
        self.assertEqual(models["deepseek-v4-1-flash"]["release_date"], "2026-09-10")
        self.assertEqual(models["gemini-4-argon"]["release_date"], "2026-09-30")
        self.assertEqual(models["claude-fable-5-1"]["release_date"], "2026-09-01")
        self.assertEqual(models["qwen3-8-max"]["release_date"], "2026-08-03")
        self.assertEqual(models["kimi-k3"]["release_date"], "2026-07-16")
        self.assertEqual(models["gpt-6-sol"]["release_date"], "2026-09-22")
        self.assertEqual(models["gpt-6-luna"]["release_date"], "2026-09-22")
        self.assertIsNone(models["qwen3-7-max"]["release_date"])
        self.assertIsNone(models["qwen3-8-flash-next"]["release_date"])
        self.assertIsNone(models["qwen3-8-2-4t-a95b"]["release_date"])
        self.assertIsNone(models["qwen3-max-thinking"]["release_date"])
        self.assertIsNone(models["qwen-max"]["release_date"])
        self.assertIsNone(models["deepseek-v4-vision-exp"]["release_date"])
        self.assertIsNone(pubs["publication-anthropic-claude-fable-5-1"]["published_at"])
        self.assertIsNone(pubs["publication-google-gemini-4-argon"]["published_at"])

    def test_payload_matches_committed_file(self):
        out = ROOT / "public" / "benchmarks.v1.json"
        self.assertTrue(out.exists(), "run python -m tools.benchdb build")
        text = build.render(build.build_payload(self.db, build.sha256_of(DATA)))
        self.assertEqual(out.read_text(encoding="utf-8"), text)

    def test_compact_payload_matches_committed_file_and_decodes_to_the_full_one(self):
        out = ROOT / "public" / "benchmarks.v1.compact.json"
        self.assertTrue(out.exists(), "run python -m tools.benchdb build")
        payload = build.build_payload(self.db, build.sha256_of(DATA))
        small = compact.encode(payload)
        self.assertEqual(out.read_text(encoding="utf-8"), build.render(small))
        self.assertEqual(compact.decode(json.loads(out.read_text(encoding="utf-8"))), payload)
        self.assertLess(out.stat().st_size * 4, (ROOT / "public" / "benchmarks.v1.json").stat().st_size)


if __name__ == "__main__":
    unittest.main()
