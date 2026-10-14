# Data contract

`data/database.json` is the source. `tools/benchdb/validate.py` enforces everything below; a rule that is not in this file is not enforced, and a new kind of source or unit extends this file first.

## Top level

| Field | Rule |
|---|---|
| `schema_version` | Semantic version of this contract. |
| `data_version` | `YYYY-MM-DD.N`. Bumped on every accepted data change. |
| `as_of` | `YYYY-MM-DD`. Never older than the last change log entry. |
| `default_publication_id` | The publication the article opens with. Must exist. |
| `comparison_policy` | Free text the article shows. Score selection, missing values, percent rule, no overall ranking. |
| `taxonomy_note` | Why the categories are editorial. |
| `categories`, `families`, `benchmarks`, `models`, `publications`, `observations`, `change_log` | The records below. |
| `research_catalog` | Internal working material. Never exported to the payload. The only place where imported labels keep their original punctuation. |

## Text

Outside the research catalog, no string may contain an em dash, an en dash or an emoji. A range in a label is written with "to" (`256k to 1M`). Labels are otherwise kept as the publisher printed them.

## Records

### categories

`id` (kebab-case, unique), `name_en`, `name_ru`, `order` (unique), `description`. Twenty editorial categories; a family belongs to exactly one.

### families

`id` (unique), `name`, `category_id` (must exist), `tags`, `priority`, `published_by`, `vendor_flags_scope`, `catalog_order`. A family is navigation, never a unit of comparison.

### benchmarks

One record per exact test, version and metric.

| Field | Rule |
|---|---|
| `id` | kebab-case, unique, ends with `--<unit>`. |
| `family_id`, `category_id` | Must exist. |
| `name`, `version`, `version_label`, `metric_label` | Version may be null; labels are required. |
| `unit` | `percent`, `score`, `elo`, `usd` or `fraction`. |
| `unit_denominator` | Required for `usd` (for example `task`), otherwise null. |
| `higher_is_better` | Boolean. False for cost, refusal and error rates. |
| `definition_status` | `source_label_preserved` until a benchmark is documented independently. |
| `cross_publication_equivalence` | `not_established` unless two publications are shown to use one protocol. |

### models

`id` (kebab-case, unique), `name`, `developer`, `identity_scope`, `release_date` (date or null).

A result printed under another model's heading gets its own identity: the id contains `reported-as` and the name contains "reported as". Mythos results printed under a Fable column are the standing example.

### publications

`id` (unique), `name`, `publisher`, `url` (https), `source_id`, `published_at` (date or null), `checked_on` (date), `kind` (`official_release_comparison`, `model_card`, `official_blog`), `comparison_scope` (`publisher_comparison`), `methodology_url`, `coverage` (what of the page was transcribed).

### observations

One record per number on a page.

| Field | Rule |
|---|---|
| `id` | `obs-` plus 20 hex characters, unique, never reused. |
| `benchmark_id`, `model_id`, `publication_id` | Must exist. |
| `value` | A number. Percent in 0..100, fraction in 0..1, elo a positive integer, usd not negative. |
| `unit`, `unit_denominator` | Must equal the benchmark's. |
| `conditions` | Object with exactly the known keys: `model_label_as_published`, `benchmark_label_as_published`, `setup_as_reported`, `model_setup_as_reported` (all required), `reasoning_effort`, `harness`, `tools`, `fallback_policy`, `attempt_budget`, `context_tokens`, `dataset_revision` (null when the publisher did not say), `protocol_equivalence` (required). |
| `source_url` | https. The page the number is on. |
| `source_locator` | Where on the page: table name, section, page number. |
| `methodology_url` | Optional. |
| `checked_on` | Date the number was read from the page. |
| `evidence_type` | `official_publication_checked`. Imported, unverified rows never carry this value and never enter `observations`. |
| `review_status` | `source_checked`. |
| `status` | `active`, `superseded` or `withdrawn`. Only active rows reach the payload. |
| `comparison_scope` | `publisher_comparison`. |
| `supersedes` | Id of the row this one replaces, or null. |

Two active rows may share one (benchmark, model, publication) only when a distinguishing condition differs: effort, harness, tools, fallback, attempt budget, context length or dataset revision. The same number twice is refused. A corrected number is a new row with `supersedes` pointing at the old one, and the old one becomes `superseded`.

### change_log

Append-only list of `{at, reviewer, reason, added_observations}`. The article shows it as the update history.

## No loss

`build` compares the database with the committed payload. Every observation id the payload carries must still exist in the database, in any status. A row may be superseded or withdrawn; it may not disappear.

## Units in the article

- `percent` is shown with a percent sign.
- `score` is shown as a number. A Qwen `score` is not a percent and must not be labeled as one.
- `elo` is shown as an integer. It is never converted to a percent.
- `usd` is shown with the denominator (`5.47 per task`).
- A missing result is a dash.

## Research catalog

`research_catalog` holds a benchmark registry, model configurations and family evidence pulled from third-party catalogs, plus a pointer to a local `imports/` file. These entries are navigation and candidate material: not verified scores, never exported, never matched to observations by name similarity. Promoting a candidate means reading the publisher's page and creating an observation by the runbook.
