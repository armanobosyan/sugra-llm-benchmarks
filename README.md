# Sugra LLM Benchmarks

A reviewed catalog of benchmark results that AI model publishers have printed in their own release pages and model cards. Every number is stored as the publisher reported it, with the publication, the place on the page, the date it was checked and the conditions the publisher stated. Nothing here is a benchmark run of our own, and nothing is a ranking.

The catalog feeds the comparison article on the Sugra Systems blog. The article reads the built payload, so a change to the data becomes a change on the page after one accepted pull request.

## Layout

| Path | What it is |
|---|---|
| `data/database.json` | The checked catalog. Categories, benchmark families, benchmark definitions, model identities, publications, observations, official prices and the change log. |
| `public/benchmarks.v1.json` | The built payload the article loads. Generated, committed, checked in CI. Never edit by hand. |
| `tools/benchdb/` | `validate` and `build`, standard library only. |
| `tests/` | Contract tests plus checks against the real database. |
| `DATA-CONTRACT.md` | What every record must contain and the rules the validator enforces. |
| `UPDATE-RUNBOOK.md` | How to add a publication or a result, step by step. |
| `COVERAGE.md` | What is in the catalog today, and what is not. |

`imports/` (candidate rows pulled from third-party catalogs) stays local and is never published.

## Commands

```
python -m tools.benchdb validate
python -m tools.benchdb build
python -m tools.benchdb build --check
python -m unittest discover -s tests -v
```

Python 3.12 or newer, no dependencies.

## How to read a number

- A value is comparable only with the other values of the same publication. Publishers use different harnesses, efforts and tool settings, and the catalog does not claim that two publications measured the same thing.
- When one model has two results for one test in one publication (for example Max and Xhigh effort), both are stored. The catalog never picks the higher one.
- `percent` gets a percent sign. `score`, `elo` and `usd` are shown in their own units.
- A model with no result for a test shows a dash, not a zero.
- A result a publisher printed under one model's name while its footnote names another configuration is stored under the model the heading names, and the footnote stays on the result (`conditions.model_setup_as_reported`).
- A token price is not a benchmark result. It lives in `prices`, taken from that developer's own price page. The payload's `counts.prices` is the number of active prices. A missing end date means the page did not state one.

## Taxonomy

The twenty categories are an editorial navigation aid for this catalog. They are not an industry standard, and a benchmark family sits in one category with tags for the overlaps. The unit of comparison is always the exact benchmark version and metric, never the family. Each category carries a reader-facing description, and each family a benchmark uses carries an `about` block (maintainer, what it tests, year, the page it was written from, and a status that says whether the text was checked against the maintainer's own page). The article prints both under the table.

## Updating

Open a pull request that changes `data/database.json`, run `build` and commit the payload with it. CI refuses a stale payload, a lost observation and any record that breaks the contract. The runbook has the full procedure.

## Licence

The code under `tools/` and `tests/` is MIT (see `LICENSE`). The catalog under `data/` and the built payload under `public/` are published under CC BY 4.0: reuse them with a credit to Sugra Systems, Inc. and a link to this repository. Every number in `data/database.json` and in the built payload remains the statement of the publisher that printed it, cited by publication and locator. The licence covers the compilation and the descriptions, not the publishers' pages.
