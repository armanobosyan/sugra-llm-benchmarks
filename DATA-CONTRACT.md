# Data contract

`data/database.json` is the source. `tools/benchdb/validate.py` enforces the structural rules in this file: ids, references, kinds, units, dates, punctuation, the price publisher, and one row when two labels carry the same values. It does not re-read a publisher page, and it does not fill a missing field. A rule that is not in this file is not enforced, and a new kind of source or unit extends this file first.

## Top level

| Field | Rule |
|---|---|
| `schema_version` | Semantic version of this contract. |
| `data_version` | `YYYYMMDDNN`: the date and a two-digit sequence within the day, for example `2026101402`. Bumped on every accepted data change; the article and its exports show it as is. |
| `as_of` | `YYYY-MM-DD`. Never older than the last change log entry. |
| `default_publication_id` | The publication the article opens with. Must exist. |
| `comparison_policy` | Free text the article shows. Score selection, missing values, percent rule, no overall ranking. |
| `taxonomy_note` | Why the categories are editorial. |
| `categories`, `families`, `benchmarks`, `models`, `publications`, `observations`, `prices`, `change_log` | The records below. `prices` is required from schema 1.1.0 and may be an empty list. A 1.0.0 database may omit it. |

There is no draft file beside the score file. `validate` and `build` read `data/database.json` only. A `research_catalog` key pasted into the score file is ordinary text: `validate` checks it, and `build` leaves it out of the payload.

## Text

No string in `data/database.json` may contain an em dash, an en dash or an emoji. A range in a label is written with "to" (`256k to 1M`). Labels are otherwise kept as the publisher printed them. Every string in that file is English.

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

One record per exact test, version and metric. A publisher's own label for a test lives in the observation's `benchmark_label_as_published`, never in a second record: two records of one family in the same unit whose shared models (two or more) all carry equal values are refused by the validator.

| Field | Rule |
|---|---|
| `id` | kebab-case, unique, ends with `--<unit>`. |
| `family_id`, `category_id` | Must exist. |
| `name`, `version`, `version_label`, `metric_label` | Version may be null; labels are required. |
| `unit` | `percent`, `score`, `elo`, `usd` or `fraction`. |
| `unit_denominator` | Required for `usd` (for example `task`), otherwise null. |
| `higher_is_better` | Boolean. False for cost, refusal and error rates. |
| `definition_status` | `source_label_preserved` until a benchmark is documented independently. The checker requires the field. It does not decide whether a definition has been documented independently. |
| `cross_publication_equivalence` | `not_established` unless two publications are shown to use one protocol. |

### models

`id` (kebab-case, unique), `name`, `developer`, `identity_scope`, `release_date` (date or null). `latest` (true or false, optional, default false): the newest model of its developer, the set the table's Latest chip selects; at most one per developer.

A result printed under one model's heading while a footnote names another configuration belongs to the model the heading names; the footnote is kept on the observation in `conditions.model_setup_as_reported`, never in a second model identity. The three Mythos results printed under Fable headings on the GPT-6 Astra page are the standing example.

### publications

`id` (unique), `name`, `publisher`, `url` (https), `source_id`, `published_at` (date or null), `checked_on` (date), `kind`, `comparison_scope`, `methodology_url`, `coverage` (what of the page was transcribed).

`kind` is `official_release_comparison`, `model_card` or `official_blog` with `comparison_scope` `publisher_comparison`, or `official_price_list` with `comparison_scope` `price_list`. A price list is not a benchmark publication: observations cannot reference it, and a price cannot reference any other kind. The publisher string must equal `models.developer` for every price on that list. A number printed by a different lab is not that model's price.

### observations

One record per number on a page.

| Field | Rule |
|---|---|
| `id` | `obs-` plus 20 hex characters, unique, never reused. |
| `benchmark_id`, `model_id`, `publication_id` | Must exist. |
| `value` | A number. Percent in 0..100, fraction in 0..1, elo a positive number (a decimal stays as printed), usd not negative. |
| `unit`, `unit_denominator` | Must equal the benchmark's. |
| `conditions` | Object. Required and non-empty: `model_label_as_published`, `benchmark_label_as_published`, `setup_as_reported`, `model_setup_as_reported`, `protocol_equivalence`. Allowed, and omitted or null when the publisher did not say: `reasoning_effort`, `harness`, `tools`, `fallback_policy`, `attempt_budget`, `context_tokens`, `dataset_revision`. Any other key is refused. The checker does not fill a missing key. |
| `source_url` | https. The page the number is on. |
| `source_locator` | Where on the page: table name, section, page number. |
| `methodology_url` | Optional. |
| `checked_on` | Date the number was read from the page. |
| `evidence_type` | `official_publication_checked`. Imported, unverified rows never carry this value and never enter `observations`. |
| `review_status` | `source_checked`. |
| `status` | `active`, `superseded` or `withdrawn`. Only active rows reach the payload. |
| `comparison_scope` | `publisher_comparison`. |
| `supersedes` | Id of the row this one replaces, or null. |

Two active rows may share one (benchmark, model, publication) only when a distinguishing condition differs: effort, harness, tools, fallback, attempt budget, context length, dataset revision, or `model_setup_as_reported` when the page prints a second configuration in the same cell (a Mythos value under a Fable heading). The same number twice is refused. A corrected number is a new row with `supersedes` pointing at the old one, and the old one becomes `superseded`.

### prices

One record per number on an official price page. A price is not an observation: it is never a benchmark result, and the article must not rank it as one.

| Field | Rule |
|---|---|
| `id` | kebab-case, unique, starts with `price-`. |
| `model_id`, `publication_id` | Must exist. The publication is an `official_price_list`, and its publisher equals the model's developer. |
| `component` | `input`, `cached_input`, `cache_write`, `cache_write_5m`, `cache_write_1h`, `output`, `storage` or `generation`. Only a component the page prints. Cache hit or cache read is `cached_input`. A single per-image, per-video or per-page price is `generation`. |
| `value` | A number >= 0. Zero is a printed free price, not a missing cell. A missing cell is no record. |
| `unit` | `usd_per_million_tokens`, `usd_per_million_tokens_per_hour`, `usd_per_image`, `usd_per_second`, `usd_per_minute`, `usd_per_video`, `usd_per_million_chars`, `usd_per_thousand_pages`, or `cny_per_million_tokens` when the page prints yuan. Do not convert currencies. |
| `schedule` | `standard`, `batch`, `fast`, `flex`, `ultrafast`, `peak`, `off_peak`, `priority`, `contributor` or `free`. A multiplier the page states without printing the resulting cells (a regional uplift, a batch percent) is coverage text, not a computed row. |
| `context_band` | `short`, `long` or `any`. |
| `context_threshold_tokens` | Positive integer when the band is `short` or `long`, otherwise null. The threshold is the one the page prints. |
| `modality` | `text`, `image` or `video`. |
| `region` | kebab-case when the page prints a separate regional price, otherwise null. |
| `meter` | kebab-case when one component is priced twice on the page and the other fields cannot tell the rows apart (annotated pages beside pages, 720p beside 4k, or a context range that is not a single short/long split), otherwise null. |
| `offer` | `list` or `promotional`. |
| `valid_from`, `valid_until` | Date or null. Null means the page stated no such date. Do not invent an end for a sale. |
| `checked_on` | Date the number was read. |
| `source_url`, `source_locator` | https, and where on the page the number is. |
| `status` | `active`, `superseded` or `withdrawn`. Only active rows reach the payload. |
| `note` | Optional. A condition the page states that the fields above do not carry. |

Two active rows may not share one (model, publication, component, schedule, band, region, modality, offer, meter, valid_from, valid_until). A corrected price is a new row. The payload drops null fields, so a missing `valid_until` there means the page gave no end date.

### change_log

Append-only list of `{at, reviewer, reason, added_observations}`. The article shows it as the update history.

## Two payload files

`build` writes `public/benchmarks.v1.json`, every active record in plain JSON, and `public/benchmarks.v1.compact.json`, the same records in a smaller shape. The compact file keeps each distinct string once in `strings` and writes every observation and price as an array of cells in the order `observation_columns`, `condition_columns` and `price_columns` give: a text cell is its 1-based index into `strings`, a number cell is a one-element list such as `[93.4]`, `0` is an absent field, and a row drops its trailing absent cells. Every other top-level field is copied as it is, and `encoding` is `"columns"`. Decoding the compact file gives the full file field for field; `tools/benchdb/compact.py` holds both directions and the tests check the round trip on the committed data. `build --check` refuses a stale copy of either file.

## No loss

`build` compares the database with the committed payload. Every observation id the payload carries must still exist in the database, in any status. The same rule applies to price ids once a payload has carried them. A row may be superseded or withdrawn; it may not disappear.

## Units in the article

- `percent` is shown with a percent sign.
- `score` is shown as a number. A Qwen `score` is not a percent and must not be labeled as one.
- `elo` is shown as printed, decimals included. It is never converted to a percent.
- `usd` is shown with the denominator (`5.47 per task`).
- A missing result is a dash.
- A token price is not a benchmark cell. It is a `prices` record. The payload carries active prices under `prices`, and `counts.prices` is how many.

## Draft keys

This repository does not publish a third-party draft. A score is added by reading the publisher's own page and following the runbook. If a `research_catalog` key is pasted into the score file, `validate` checks that text and `build` leaves it out of the payload. An imported row is not matched to an observation by name.
