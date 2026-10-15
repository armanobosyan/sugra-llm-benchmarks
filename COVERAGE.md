# Coverage

What the catalog holds, and what it does not. The benchmark slice is still the 2026-10-14 transcription (596 observations, data version 2026101402). Official prices were added on 2026-10-15; the catalog data version is now 2026101501. Counts come from `data/database.json`; the tests in `tests/` pin the seed so a later version can only add.

## Publications transcribed

| Publication | Publisher | Observations | Models | Benchmarks |
|---|---|---|---|---|
| Gemini 4 Argon | Google | 73 | 4 | 19 |
| Claude Opus 5.5 | Anthropic | 39 | 5 | 9 |
| Claude Sonnet 5.5 | Anthropic | 29 | 4 | 8 |
| GPT-6 Astra | OpenAI | 149 | 8 | 40 |
| GPT-6.1 Sol | OpenAI | 10 | 5 | 4 |
| Grok 4.7 model card | xAI | 145 | 11 | 38 |
| Qwen3.8-Max comparison | Alibaba | 151 | 5 | 32 |

Seven publications, 596 observations, 21 models in that slice, 129 benchmark definitions in 97 families. The file now also holds the priced models named below. The 596 observations are unchanged.

Only rows the publisher printed as text or a table were transcribed. Values that exist only inside an interactive chart were not, unless the article text also prints them. Each publication's `coverage` field says what was left out.

## Official prices

Checked on 2026-10-15 against each publisher's own price page. Schema 1.1.0. A price is not a benchmark observation: it lives in `prices`, and the benchmark publications above are untouched.

| Price list | Publisher | Rows |
|---|---|---|
| OpenAI API pricing | OpenAI | 641 |
| Anthropic API pricing | Anthropic | 153 |
| Gemini API pricing | Google | 389 |
| xAI API pricing | xAI | 60 |
| Alibaba Model Studio pricing | Alibaba | 988 |
| DeepSeek API pricing | DeepSeek | 12 |
| Kimi API pricing | Moonshot AI | 14 |
| Mistral API pricing | Mistral | 24 |
| Z.AI API pricing | Z.AI | 86 |

2,367 price rows. 298 models were added because a price page names them. `latest` is still one flagship per developer and was not changed.

Text rates are USD per 1,000,000 tokens, except Kimi, which stays in CNY because that is the unit on the page. Image, video, and OCR use the unit the page prints (per image, per second, per video, per 1,000 pages) when that number is the price itself. A parenthetical "equivalent to" is not stored as a second price. Where the page prints a short context band and a long one, both are stored with the printed threshold. Where it prints an end date, the row carries that date. A sale or introductory price with no printed end date has no invented end date.

Left in each price publication's coverage, not expanded into rows: audio, voice, live, transcription, TTS, tools, fine-tuning, and a regional multiplier the page states without printing every cell. A model hosted on another lab's page is not given that host's price. Mistral's page quotes GLM 5.3 cached input at $0.14; Z.AI's own page prints $0.26, and only the Z.AI row is stored. DeepSeek still prints V4-Pro prices on the price page. Meta has no public token price, so there is no Meta price row.

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

Every family that a benchmark uses carries a description for the reader (`about` in `families`). Status today: 69 checked against the maintainer's own page or paper, 28 written from secondary coverage or from the name alone (each one's `notes` says what is missing), 0 pending. A reader sees the status on the page: an unverified description carries a note, a pending one is printed as pending.

Two categories are empty in this version. They stay in the taxonomy because the research catalog lists families for them; the article hides a category with no rows for the selected publication.

## Known gaps

- `release_date` is null for every model and `published_at` for every publication: the pages were checked, their publication dates were not recorded yet.
- `reasoning_effort` is stated for 176 observations, `tools` for 30, `harness` for none. Where the publisher did not say, the field is null; the page-level setup text is in `conditions.setup_as_reported`.
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
