# Data contract

`data/database.json` is the source. `tools/benchdb/validate.py` enforces everything below; a rule that is not in this file is not enforced, and a new kind of source or unit extends this file first.

## Top level

| Field | Rule |
|---|---|
| `schema_version` | Semantic version of this contract. |
| `data_version` | `YYYYMMDDNN`: the date and a two-digit sequence within the day, for example `2026101402`. Bumped on every accepted data change; the article and its exports show it as is. |
| `as_of` | `YYYY-MM-DD`. Never older than the last change log entry. |
| `default_publication_id` | The publication the article opens with. Must exist. |
| `comparison_policy` | Free text the article shows. Score selection, missing values, percent rule, no overall ranking. |
| `taxonomy_note` | Why the categories are editorial. |
| `categories`, `families`, `benchmarks`, `models`, `publications`, `observations`, `change_log` | The records below. |
| `research_catalog` | Internal working material. Never exported to the payload. The only place where imported labels keep their original punctuation. |

## Text

Outside the research catalog, no string may contain an em dash, an en dash or an emoji. A range in a label is written with "to" (`256k to 1M`). Labels are otherwise kept as the publisher printed them. Every string in the database, the research catalog included, is English.

## Records

### categories

`id` (kebab-case, unique), `name_en`, `order` (unique), `description_en`. Twenty editorial categories; a family belongs to exactly one. `description_en` is the reader-facing paragraph the article prints at the head of each category in its glossary: what the category covers, how its tests are usually scored, and what it deliberately leaves to a neighbour.

### families

`id` (unique), `name`, `category_id` (must exist), `tags`, `priority`, `published_by`, `vendor_flags_scope`, `catalog_order`, `about`. A family is navigation, never a unit of comparison.

`about` is required on every family that a benchmark uses and describes the test for a reader: who maintains it, what it asks the model to do, how it is scored, and when it appeared.

| Field | Rule |
|---|---|
| `maintainer` | The organisation or authors that maintain the test, as its own page or paper names them. Never the publisher that printed a result, unless they are the same. |
| `url` | The maintainer's page, paper or repository, `https://` only, or null. |
| `what_it_tests` | A short paragraph in plain English: the task, the material, the scoring. Required unless `status` is `pending`. No scores: a number belongs in an observation. |
| `introduced` | Four-digit year or null. |
| `status` | `checked`: the text was written from the maintainer's own page or paper. `unverified`: written from secondary coverage or from the name alone, and `notes` says what is missing. `pending`: no text yet. |
| `evidence_url` | The page the text was written from, `https://` only, or null. |
| `notes` | Anything a reader should know: a label that does not match the maintainer's name, a conflict between sources, a missing primary source. |

The article renders `what_it_tests`, the maintainer link and the note under the table, and shows a `pending` family as "description pending" rather than hiding it.

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

`id` (kebab-case, unique), `name`, `developer`, `identity_scope`, `release_date` (date or null). `latest` (true or false, optional, default false): the newest model of its developer, the set the table's Latest chip selects; at most one per developer.

A result printed under one model's heading while a footnote names another configuration belongs to the model the heading names; the footnote is kept on the observation in `conditions.model_setup_as_reported`, never in a second model identity. The three Mythos results printed under Fable headings on the GPT-6 Astra page are the standing example.

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
