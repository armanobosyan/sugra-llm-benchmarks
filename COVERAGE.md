# Coverage

What the catalog holds as of data version 2026101508, and what it does not. Counts come from `data/database.json`; the tests in `tests/` pin the seed so a later version can only add.

## Publications transcribed

| Publication | Publisher | Observations | Models | Benchmarks |
|---|---|---|---|---|
| Gemini 4 Argon | Google | 73 | 4 | 19 |
| Claude Opus 5.5 | Anthropic | 39 | 5 | 9 |
| GPT-6 Astra | OpenAI | 149 | 6 | 40 |
| GPT-6.1 Sol | OpenAI | 10 | 5 | 4 |
| Qwen3.8-Max comparison | Alibaba | 151 | 5 | 32 |
| Grok 4.7 model card | xAI | 145 | 11 | 38 |
| Claude Sonnet 5.5 | Anthropic | 29 | 4 | 8 |
| Claude Haiku 5.5 | Anthropic | 29 | 4 | 8 |
| Claude Fable 5.1 and Mythos 5.1 | Anthropic | 33 | 4 | 9 |
| Gemini 3.8 Flash model card | Google | 85 | 6 | 14 |
| Gemini 3.7 Flash model card | Google | 84 | 5 | 20 |
| Introducing Grok 4.6 | xAI | 39 | 4 | 10 |
| DeepSeek-V4.1-Flash model card | DeepSeek | 125 | 7 | 19 |
| GLM-5.3 model card | Z.ai | 120 | 8 | 17 |

Fourteen publications, 1111 observations, 31 models, 163 benchmark definitions in 108 families.

Only rows the publisher printed as text or a table were transcribed. Values that exist only inside an interactive chart were not, unless the article text also prints them. Each publication's `coverage` field says what was left out.

## Categories

| Category | Benchmarks | Observations |
|---|---|---|
| Knowledge work | 15 | 86 |
| Agentic coding | 19 | 137 |
| ML engineering | 4 | 17 |
| Science and math | 14 | 62 |
| Long context | 6 | 20 |
| Computer use | 3 | 14 |
| Multimodal understanding | 4 | 17 |
| Cybersecurity | 12 | 42 |
| General knowledge and reasoning | 8 | 38 |
| Code generation | 2 | 10 |
| Tool use and workflows | 6 | 25 |
| Web search and research | 2 | 8 |
| Instruction following | 1 | 5 |
| Multilingual | 0 | 0 |
| Writing and conversation | 0 | 0 |
| Healthcare | 3 | 15 |
| Biosecurity | 8 | 27 |
| Safety and alignment | 17 | 48 |
| Engineering and design | 4 | 19 |
| Preference and composite rankings | 1 | 6 |

Every family that a benchmark uses carries a description for the reader (`about` in `families`). Status today: 95 checked against the maintainer's own page, the developer page or paper that prints the test, 13 written from the printed label alone (each one's `notes` says what is missing), 0 pending. A reader sees the status on the page: an unverified description carries a note, a pending one is printed as pending.

Two categories are empty in this version. They stay in the taxonomy because the research catalog lists families for them; the article hides a category with no rows for the selected publication.

## Known gaps

- `release_date` is recorded for 11 of 31 models and `published_at` for 4 of 14 publications; the rest were checked before dates were recorded and fill in as their pages are read again.
- `reasoning_effort` is stated for 302 observations, `tools` for 83, `harness` for 40. Where the publisher did not say, the field is null; the page-level setup text is in `conditions.setup_as_reported`.
- No publication has `cross_publication_equivalence` established for any benchmark. The article therefore shows one publication at a time by default.
- Google's row-specific exceptions (effort or fallback that differ from the headline setup) are recorded in the methodology text, not yet as per-row condition fields.
- Several launch pages attribute a test to the publisher itself where the maintainer's page names someone else (an academic group, an evaluation firm). The `about.maintainer` field follows the maintainer's page and `about.notes` records the mismatch; the printed attribution stays in the observation as printed.
- Independent sources (leaderboards, third-party evaluations) are absent. Adding one is a new `kind` and a new `evidence_type`, which means extending the contract and its tests first.

## Research catalog (not published)

The database carries a working catalog: 318 benchmark registry entries, 897 model configurations and 634 family evidence rows, gathered from third-party catalogs, plus a pointer to a local import file of 9,749 candidate rows that is not committed. None of this is verified and none of it reaches the payload. It is a map of where to look next, in this order:

1. New official releases from the five publishers already covered.
2. System cards and model cards not yet transcribed.
3. Exact values behind dynamic charts, when a publisher also prints them.
4. Independent sources, after the contract is extended for them.
