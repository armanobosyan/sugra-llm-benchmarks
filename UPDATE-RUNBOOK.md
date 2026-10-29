# Update runbook

Every change to the catalog is one pull request that changes `data/database.json`, rebuilds `public/benchmarks.v1.json` and `public/benchmarks.v1.compact.json` (one `build` writes both) and passes CI. Numbers are never edited in the article or its components.

## 1. Add a publication

1. Open the publisher's page. Note the URL, the date you read it, and which table or section you transcribe.
2. Add a `publications` record: `id` as `publication-<publisher>-<model>`, `kind`, `checked_on`, `coverage` saying what you transcribed and what you left out (interactive charts, footnote-only numbers).
3. Add any new `models`. A result printed under another model's heading but attributed in a footnote to a different configuration stays under the model the heading names; the footnote goes into `conditions.model_setup_as_reported` on the observation, never into a second model identity.
4. Add any new `benchmarks`. One record per exact test, version and metric; the id ends with `--<unit>`. Check the family exists in `families`, add it with its category if not, and write its `about` block (section 2a). A new category needs `description_en` too.
5. Add `observations` (section 2).
6. Append a `change_log` entry, bump `data_version` and `as_of`.

## 1b. Add a price

A price is not an observation. Do not put it in `observations`, or a table that shades the best cell in a row will shade the cheapest model.

1. Open the developer's own price page. A figure on another lab's page is not this model's price.
2. Add one `official_price_list` publication for that page (`comparison_scope` `price_list`) if it is not there yet. `coverage` names what was transcribed and what was left as a rule instead of a row (a regional multiplier, a batch discount stated only as a percent, audio, tools, training hours).
3. Add a `models` record for a SKU that is not already in the catalog. `latest` stays false unless that developer has no latest model and this one is the flagship the developer lists first. Do not move `latest` off the current flagship just because a smaller model is newer.
4. Add one `prices` row per printed number: component, schedule, context band and the page's threshold, modality, region, meter, offer, and `valid_from` / `valid_until` only when the page states them. A printed zero is free. A dash is no row. Do not compute a discount the page only describes as a multiplier. Do not convert yuan to dollars.
5. Append a `change_log` entry with `added_observations` 0, and bump `data_version` and `as_of`.

## 1c. Add model facts

Facts are what the developer prints about the model itself: context window, max output, input and output modalities, open or closed weights, and the licence of open weights (DATA-CONTRACT.md, models).

1. Open the developer's own page for that model: the API model page or the models overview, the model card, its Hugging Face organisation. A figure on another lab's page, an aggregator or a sibling model's page is not this model's fact.
2. Fill each fact the page prints, with `as_printed`, `source_url`, `source_locator` and `checked_on`. A fact the page does not print stays null; do not carry one over from the previous model of the family.
3. Append a `change_log` entry with `added_observations` 0, and bump `data_version` and `as_of`.

## 2. Add an observation

For every number on the page:

- `id`: `obs-` plus 20 hex characters. Generate with `python -c "import secrets; print('obs-' + secrets.token_hex(10))"`.
- `value` as printed, in the publisher's unit. Do not convert fractions to percent, Elo to percent, or round.
- `conditions`: the publisher's own labels for the model and the benchmark, the setup text from the page, and effort, harness, tools, fallback, attempt budget, context length, dataset revision when the page states them. Leave null when it does not.
- `source_locator`: table name, section, printed page number.
- `checked_on`: today.

If the same model and test already have an active row in this publication, the new row must differ in a stated condition (Max beside Xhigh). If the publisher corrected a number, add the new row with `supersedes` set and change the old row's `status` to `superseded`. Never delete a row.

## 2a. Describe a test

Every family a benchmark uses carries an `about` block, and the validator refuses a used family without one. Open the maintainer's own page or paper, not the publisher's launch page: the launch page tells you the score, the maintainer tells you what the test is.

- `maintainer` and `url`: who runs the test and where it lives. If the launch page attributes it to the publisher and the maintainer's page says otherwise, the maintainer's page wins and `notes` records the mismatch.
- `what_it_tests`: three or four sentences. The task the model is given, the material (how many problems, what kind), how a result is scored. No scores and no rankings.
- `introduced`: the year of the paper or the first release, or null.
- `status`: `checked` when you wrote from the maintainer's page or paper and `evidence_url` points to it; `unverified` when only secondary coverage or the name was available, with `notes` saying so; `pending` when you add the family now and the text later. A `pending` family is printed as "description pending" in the article, so it is visible, not forgotten.

`COVERAGE.md` lists the count of each status; update it when a status changes.

## 3. Build and check

```
python -m tools.benchdb validate
python -m tools.benchdb build
python -m unittest discover -s tests -v
```

Commit `data/database.json` and `public/benchmarks.v1.json` together. CI runs `build --check`, so a payload that does not match the database fails the pull request.

## 4. Pull request

Title: what changed in one line (`Add xAI Grok 4.8 model card, 61 observations`). Body: the publication URL and the change log reason. One reviewer reads a sample of rows against the page.

## 5. After merge

The blog rebuilds from the main branch payload. The article shows `data_version` and `as_of` under the table and stamps both exports with them; the change log stays in the file. Check the page once it is live.

## What never happens

- A number is not chosen because it is the highest or the latest.
- An imported catalog row is not promoted by name similarity.
- A field is not changed to make the validator pass; the contract is extended instead, with its tests.
- The payload is not edited by hand.
