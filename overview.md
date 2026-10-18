# Hetu: technical overview

A guide for anyone joining the project: what Hetu does, how the pieces fit together, where each feature
lives, and what is still rough. For setup commands, see [README.md](README.md).

---

## 1. What Hetu does

Hetu takes an Indian criminal case and puts three stories about it side by side:

| Story | Source | What Hetu extracts |
|---|---|---|
| The court's story | The final judgment | Facts, motive, trigger, reasoning, outcome, legal provisions, timeline |
| The media's story | News articles | Framing, tone, narratives, and each factual claim checked against the judgment |
| The public's story | Public reader comments | Stance (support victim / support accused / neutral / against media bias) and themes |

It then scores how far the media and public narratives drift from the court's findings: the
**Perception Gap Index**, 0 (aligned) to 100. Every number on the dashboard links to the exact passage it came
from.

Ground rules that shape the code: public content only, robots.txt respected, no logins or CAPTCHAs; private people
anonymized before storage; no individual profiling; no outcome prediction; every claim cites its source.

---

## 2. Architecture

```
                       ┌──────────────────────── backend (FastAPI, Python) ────────────────────────┐
 Browser                │                                                                            │
 ┌──────────┐  /api/*   │  api/            services/jobs.py        agents/ (TinyFish)                 │
 │ Next.js  │ ────────▶ │  POST /cases ──▶ background job ──────▶ JudgmentAgent ─┐                    │
 │ frontend │  (proxy)  │  GET /jobs/{id}   live log               MediaAgent ───┤─▶ case bundle      │
 │          │ ◀──────── │  GET /cases/...                                         │   (cached JSON)   │
 └──────────┘           │        ▲                                                ▼                   │
                        │        │                         services/pipeline.py                       │
                        │        │                         extraction (LLM) ─▶ anonymizer ─▶ scoring  │
                        │        │                                                │                   │
                        │  db/repository.py ◀──────────────────────────────────── save                │
                        │  SQLite (local) / Postgres (Docker)                                          │
                        └────────────────────────────────────────────────────────────────────────────┘
 External: TinyFish Agent API · Indian Kanoon · Bing News · news sites · Groq / OpenAI / Anthropic APIs
```

**Data flow for one case**

1. A case name comes in from the UI (`POST /cases`) or the CLI (`python -m app.cli collect "..."`).
2. **Collection.** TinyFish browser agents find the judgment and news coverage, and read public comments. The
   result is a *case bundle*: plain-text source documents, cached to `backend/fixtures/collected/<slug>.json`.
3. **Extraction.** An LLM turns each document into structured data. Every quote is checked word for word against
   its source.
4. **Anonymization.** Names of private people and contact details are replaced in every text field.
5. **Scoring.** The Perception Gap Index is computed from the extracted data.
6. **Storage.** The case is written to the database; the dashboard reads it through `GET /cases/{slug}`.

The **case bundle** (`backend/app/schemas/bundle.py`) is the central data format. Fixtures, collections,
extractions and the pipeline's input and output are all bundles. A bundle holds:
- `case`: slug, title, category, court, summary, `is_illustrative`
- `documents`: every source as text (`judgment`, `media`, `public`), with source name, URL and date
- `judgment`, `media`, `public`: the extracted data, empty until extraction runs

Evidence is a `Span`: a document key plus a verbatim quote. A bundle validates on load that every span points to a
real document and quotes it exactly (whitespace and curly quotes are normalized).

---

## 3. Repository structure

```
Hetu/
├── README.md                     setup and usage
├── overview.md                   this file
├── .env.example                  every setting, documented
├── docker-compose.yml            postgres + backend + frontend (production-style build)
├── docker-compose.override.yml   dev mode, loaded automatically: mounted source, live reload
│
├── backend/
│   ├── pyproject.toml            dependencies, pytest and ruff config
│   ├── Dockerfile                migrate → load demo case → serve
│   ├── alembic/versions/         database migrations (0001_initial.py)
│   ├── fixtures/
│   │   ├── jan-mat-v-state.json  illustrative demo case (already extracted)
│   │   └── collected/            TinyFish collections and extractions (git-ignored)
│   ├── scripts/export_openapi.py writes the OpenAPI schema for the frontend's typed client
│   ├── tests/                    pytest suite (no network, no API keys needed)
│   └── app/
│       ├── main.py               FastAPI app: routers, log capture, DB lifecycle
│       ├── cli.py                `python -m app.cli collect | load`
│       ├── core/config.py        all settings, read from .env
│       ├── api/
│       │   ├── health.py         GET /health
│       │   ├── cases.py          GET /cases, GET /cases/{slug}
│       │   └── jobs.py           POST /cases (start a job), GET /jobs/{id}
│       ├── agents/               TinyFish collection
│       │   ├── base.py           BaseAgent interface, CaseQuery, AgentError
│       │   ├── tinyfish.py       API client: start, poll, cancel, retries, robots.txt, step log
│       │   ├── judgment.py       JudgmentAgent (Indian Kanoon)
│       │   ├── indiankanoon.py   judgment page → exact text + metadata
│       │   ├── media.py          MediaAgent (Bing News → articles + reader comments)
│       │   └── runner.py         runs agents in parallel, caches collections
│       ├── services/
│       │   ├── pipeline.py       bundle → extraction → anonymizer → score → database
│       │   ├── extraction.py     prompts and extractors (judgment, articles, reactions)
│       │   ├── llm.py            Groq, OpenAI and Claude clients, rate limiter, retry loop
│       │   ├── anonymizer.py     names → placeholders, contact details removed
│       │   ├── scoring.py        Perception Gap Index
│       │   └── jobs.py           background jobs and their live logs
│       ├── schemas/
│       │   ├── bundle.py         case bundle and evidence checks
│       │   ├── extraction.py     what the LLM returns (structured output schemas)
│       │   └── views.py          API request and response models
│       └── db/
│           ├── session.py        async engine and sessions
│           ├── models.py         tables
│           └── repository.py     save a case; build dashboard views
│
└── frontend/                     Next.js 15 (App Router), React 19, Tailwind 4, TypeScript
    ├── Dockerfile                stages: dev (next dev) and run (standalone production server)
    └── src/
        ├── app/
        │   ├── layout.tsx        fonts, disclaimer banner, header
        │   ├── page.tsx          landing: tagline, case search, case list
        │   ├── cases/[slug]/     the case dashboard
        │   ├── jobs/[id]/        live progress page for a running case
        │   └── api/              server-side proxies to the backend (cases, jobs)
        ├── components/           dashboard sections (see §4.9)
        └── lib/
            ├── api.ts            typed API client and exported types
            ├── api/schema.d.ts   generated from the backend's OpenAPI schema
            └── format.ts         labels, colours, date and tone formatting
```

---

## 4. Features

### 4.1 Collection with TinyFish web agents (`backend/app/agents/`)

TinyFish runs a real browser that follows a plain-language `goal` from a start `url` and returns JSON shaped by an
`output_schema`. The client (`tinyfish.py`) uses the documented Agent API:
- `POST /v1/automation/run-async` to start a run
- `GET /v1/runs/{id}` to poll until `COMPLETED`, `FAILED` or `CANCELLED`
- `POST /v1/runs/{id}/cancel` to stop a run

**JudgmentAgent** (`judgment.py`) works in two steps:
1. A TinyFish agent works through Indian Kanoon's search results and returns the URL of the final judgment (the
   highest court's latest decision). It is told to stay on indiankanoon.org and not to copy text.
2. The judgment page is downloaded directly and parsed by `indiankanoon.py`, which reads the court, title,
   citations, bench and date, and returns the body text exactly as published.

The two-step design matters. An earlier version had the agent copy the whole judgment, which was slow (10+
minutes), wandered to other sites, and could paraphrase text. Exact text is required for the quote checks.

**MediaAgent** (`media.py`):
1. Searches Bing News and lists up to 6 articles from different outlets and stages of the case.
2. Reads each article in parallel and extracts the body plus up to 15 publicly visible reader comments. Commenter
   names and handles are never requested.

Articles become `media` documents and comments become `public` documents.

**Runner** (`runner.py`):
- Runs both agents concurrently. If the judgment can't be found, the other agents are cancelled at once, since a
  case can't be saved without its judgment.
- Media failures are logged, and the case continues without that coverage.
- Every collection is cached in `fixtures/collected/<slug>.json` and reused on the next run of the same case
  (`collect --refresh` forces a new one). `USE_FIXTURES=true` never calls TinyFish at all.

**Safety and robustness** (`tinyfish.py`):
- **robots.txt:** checked before any start URL or direct download. During design, Reddit, Google News, X, Quora
  and The Hindu's search pages were found to block automated access, so they are not used.
- **Ground rules:** appended to every goal: public content only; no logins, account creation, CAPTCHAs or paywalls.
- **Limits:** a per-run timeout (`AGENT_TIMEOUT_SECONDS`, default 600) cancels the remote run, and a concurrency
  cap (`TINYFISH_CONCURRENCY`, default 3) limits simultaneous runs.
- **Retries:** exponential backoff on rate limits, server errors and network errors; system failures retried.
- **Cancellation:** if our side gives up (another agent failed, or a job is stopped), the remote run is cancelled
  so it stops using credits.
- **Live steps:** each new step the browser agent reports (for example "Open the matching judgment") is logged
  and appears on the progress page.

### 4.2 LLM extraction (`backend/app/services/extraction.py`, `llm.py`)

**Providers.** `LLM_PROVIDER` picks exactly one; only its key is used, and there is no fallback.

| Provider | Client | Default model | How it returns JSON |
|---|---|---|---|
| `groq` | `GroqLLM` | `openai/gpt-oss-120b` | Chat completions with a strict `json_schema` |
| `openai` | `OpenAILLM` | `gpt-6.1-sol` | Responses API, `text.format` strict `json_schema` |
| `anthropic` (default) | `ClaudeLLM` | `claude-opus-5-5` | `messages.parse` structured outputs, server-side refusal fallback |

`make_llm()` builds the client and logs "Extracting with ..." at the start of each run. Groq and OpenAI share
`strict_schema()`, which adapts Pydantic schemas to strict mode: every property required, no extra properties,
optional fields nullable.

**Calls per case:**
- 1 for the judgment
- 1 per article
- 1 or more for public reactions (batched)

**Validate and retry** (`ask()` in `llm.py`). The LLM's output is converted and checked against the source. If a
quote isn't verbatim or a value is out of range, the call is retried (up to 3 times) with the problems listed.

**Article checks:**
- Each article is compared with the court's findings and with the **judgment passages most relevant to it**
  (`relevant_passages()`, a TF-IDF-style overlap score), not the whole judgment, which can exceed 60,000 tokens.
  Quotes are still verified against the full judgment.
- Claims whose quotes can't be verified are **dropped instead of retried**. A *supported* or *contradicted*
  verdict needs a real judgment passage, or the claim is left out; a *not in judgment* claim keeps the claim and
  drops a bad link.

**Small token budgets (Groq free plan).** `GROQ_PLAN=free` (the default) sets these limits:
- about 4,500 tokens per request, and 2,500 tokens per reply
- low reasoning effort
- a `TokenRateLimiter` keeping usage under ~7,500 tokens per minute

A judgment that doesn't fit one request is read in chunks:
1. Split it into verbatim chunks; each yields short notes (facts, motive, trigger, reasoning, outcome, events),
   each backed by a quote checked against that chunk. Unverifiable notes are dropped.
2. Narrow the notes down in selection rounds until they fit one request.
3. A final call writes the findings and cites notes by id; the evidence is the notes' exact quotes.

Article prompts and reaction batches are sized to fit the same budget.

Expect about 1 minute per ~1,400 words of judgment on the free plan, and lower quality than a single call to a
strong model (see §6).

**Failure handling:**
- Request timeouts: 2 minutes for small requests, 10 minutes for whole-document calls.
- Rate limits, refusals, cut-off output and network failures all become `ExtractionError` with a clear message.
- One failed article or reaction batch is left out instead of failing the case.

**Checkpoint.** The court's findings are saved to `<collection>.judgment.json` as soon as they are written. A
re-run reuses them if the judgment text is unchanged, and starts from the articles. This file holds names from
before anonymization, so it lives in the git-ignored collection folder.

**Extraction cache.** The finished, anonymized bundle is written to `<collection>.extracted.json`, and later runs
reuse it, so each case calls the LLM once. Use `load <file> --extract` to redo it.

### 4.3 Anonymizer (`backend/app/services/anonymizer.py`)

Runs on the whole bundle before anything is stored:
- **Names.** The LLM lists every named private person (accused, victim, witness, relative, minor, other) with
  short forms. Each person gets a stable placeholder such as `[VICTIM_1]` or `[ACCUSED_2]`, the same across
  judgment, articles and comments. Replacement is case-insensitive and word-bounded ("Ravi" doesn't match
  "Ravindra"), longest names first.
- **Contact details.** Regexes replace emails, Indian phone numbers, Aadhaar-style numbers and social handles with
  `[EMAIL]`, `[PHONE]`, `[AADHAAR]` and `[HANDLE]`.
- **Excluded fields.** Identifier and enum fields (slugs, keys, URLs, dates, verdicts) are left alone.
- **Slugs.** If the case title contained a name, the slug is rebuilt from the anonymized title plus a short hash,
  so URLs don't leak names.
- **Public figures.** Judges, lawyers and officials acting officially are not anonymized.

The public reactions table has no author column by design.

### 4.4 Perception Gap Index (`backend/app/services/scoring.py`)

`score = 100 × Σ weight × component`, where each component runs from 0 (matches the court) to 1:

| Component | Weight | Computation |
|---|---|---|
| Factual divergence | 30% | (contradicted + 0.5 × absent) / total media claims |
| Framing gap | 25% | 0.5 × share of non-procedural articles + 0.5 × mean \|tone\| |
| Public sentiment gap | 25% | Mean distance of reactions from the final outcome (opposing side 1, neutral or media-bias 0.5, same side 0) |
| Timeline distortion | 20% | Mean \|court weight − share of articles covering the event\| over judgment timeline events |

Each component stores a plain-language explanation, which the dashboard shows under "Why this score". Weights can
be passed to `perception_gap()`; they are normalized.

### 4.5 Storage (`backend/app/db/`)

**Tables:**
- `cases`
- `documents`: anonymized text and content hash, unique per case
- `judgments`: one per case; timeline and evidence stored as JSON
- `media_articles`: claims stored as JSON
- `public_reactions`
- `gap_scores`

Types are portable: JSONB on Postgres, JSON on SQLite.

`save_case()` replaces any stored version of the case, and also stores each timeline event's media share.
`get_case()` assembles the whole dashboard view, resolving every span into an `Evidence` object (quote, source
name, URL, date).

Locally the database is SQLite (`backend/hetu.db`); Docker uses Postgres. **They are separate**: a case loaded
locally is not in the Docker app, and vice versa.

### 4.6 API (`backend/app/api/`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | API and database status |
| GET | `/cases` | Case list with gap scores |
| GET | `/cases/{slug}` | Everything the dashboard shows for a case |
| POST | `/cases` | Start collecting and analysing `{name, court?, category?}`; returns a job (202) |
| GET | `/jobs/{id}` | Job status (`collecting`, `analysing`, `done`, `failed`), slug, error and live log |

FastAPI's OpenAPI schema is the contract with the frontend. After changing `schemas/views.py`, run
`python backend/scripts/export_openapi.py`, then `npm --prefix frontend run gen:api` to regenerate
`schema.d.ts`.

### 4.7 Background jobs and live progress (`backend/app/services/jobs.py`)

`POST /cases` starts an in-process asyncio task: collect, then run the pipeline, then report the case slug.
Starting a case that is already running returns the existing job.

A logging handler copies every log record emitted while a job runs into that job's event list. A context variable
keeps concurrent jobs' logs apart. The agents' and pipeline's log messages are written to be readable by users,
and private names are kept out of them.

Jobs live in memory: they disappear when the API restarts, and they only work with a single API process. Replace
`start_job()` with a real queue (for example Redis + arq) for multiple processes.

### 4.8 Command line (`backend/app/cli.py`)

```bash
python -m app.cli collect "Case name" --court "Supreme Court of India" [--refresh]
python -m app.cli load fixtures/jan-mat-v-state.json [--extract]
```

`collect` runs the agents, caches the collection, then loads it. If extraction fails, the collection is still
saved, and the error says how to `load` it later.

### 4.9 Frontend (`frontend/src/`)

All API calls happen on the Next.js server (`API_URL`, default `http://127.0.0.1:8000`; not `localhost`, which
Node may resolve to IPv6). The browser only talks to the Next.js routes in `app/api/`.

**Pages:**
- **Landing** (`app/page.tsx`): tagline, the three stories, the case search box (`CaseSearch`), and the list of
  cases with scores.
- **Progress** (`app/jobs/[id]/`, `JobProgress`): three stages (collecting, analysing, ready), a running timer, and
  the live agent log, polled every 2 seconds. It opens the dashboard when done and shows the error if a job fails.
- **Dashboard** (`app/cases/[slug]/`), top to bottom:
  - case header, with an "Illustrative demo" badge where relevant
  - `GapIndex`: the score with an expandable breakdown, and `Insights`: plain-language takeaways
  - `Timeline`: numbered events, each with court-vs-media emphasis bars and a source link
  - `CourtVsMedia`: the court's findings next to every media claim and its verdict, with a verdict summary bar
  - `PublicReaction`: a stance donut, top themes and the anonymized reactions
  - `MediaCoverage`: per-article framing, tone, narratives and claim tally
  - a sources table

Every finding, claim and event has a **§ Source** link (`EvidenceLink`) that opens the exact quote, outlet, date
and original URL.

**Design.** A dark editorial theme (`globals.css`): near-black background, ivory text, burnt-gold accents, Playfair
Display headings and Manrope body text. The chart colours (`--color-viz-1..4`) were checked for colour-blind
separation on the dark background. The disclaimer banner appears on every page.

### 4.10 Demo case

`backend/fixtures/jan-mat-v-state.json` is an **illustrative** case, *Jan Mat v. State*: prototype data, not a
real case. It has a High Court judgment, five fictional outlets' articles and 16 reactions, already extracted.
It loads with no keys or network, scores about 42, and is what the tests use. Docker loads it on every start.

### 4.11 Docker

- **`docker compose up`** uses dev mode (`docker-compose.override.yml`): `backend/` and `frontend/` are mounted,
  uvicorn runs with `--reload`, and the frontend runs `next dev`. File watching uses polling, because Docker
  Desktop on Windows doesn't pass file events from `D:\`. Rebuild with `--build` only after changing
  dependencies.
- **`docker compose -f docker-compose.yml up --build`** is the production-style build (standalone Next.js
  server, no reload).

---

## 5. Configuration (`.env`)

| Setting | Default | Purpose |
|---|---|---|
| `TINYFISH_API_KEY` | none | Required to collect cases |
| `USE_FIXTURES` | `false` | Never call TinyFish; replay cached collections only |
| `TINYFISH_CONCURRENCY`, `AGENT_TIMEOUT_SECONDS` | `3`, `600` | Parallel runs and per-run timeout |
| `LLM_PROVIDER` | `anthropic` | `groq`, `openai` or `anthropic` |
| `GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_PLAN` | none, `openai/gpt-oss-120b`, `free` | Groq; `free` turns on chunking and pacing |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | none, `gpt-6.1-sol` | OpenAI |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | none, `claude-opus-5-5` | Claude |
| `DATABASE_URL` | SQLite at `backend/hetu.db` | Docker sets Postgres |
| `API_URL` | `http://127.0.0.1:8000` | Where the frontend server reaches the API |

The demo case needs no keys.

---

## 6. Known limitations and next steps

- **Anonymizer misses name variants.** It only replaces names the LLM lists. A real run left "Jessica" and an
  alias ("Sidhartha Vashisht @ Manu Sharma") in stored data. Planned fix: split aliases (`@`, "alias",
  "a.k.a."), also redact first and last names of private people, and refuse to save if a registered name remains.
- **Groq's free plan gives low-quality results on long judgments.** On the Jessica Lal case it took about 45
  minutes and recorded the wrong outcome. Use Groq's Developer plan, OpenAI or Claude for real cases.
- **Public reactions are thin.** Most news sites have no public comment section (1 comment across 5 articles on
  the Jessica Lal case). Another public source that allows agents is needed.
- **Jobs are in memory:** lost on restart, and single-process only.
- **Not built yet:** a cross-case Insights page, and dedicated Hindi or Hinglish sentiment models (MuRIL or
  IndicBERT).
- **Docker and local use different databases.**

---

## 7. Working on the code

- **Tests:** `cd backend && pytest && ruff check .`; `cd frontend && npm run typecheck && npm run lint`. Tests use
  fakes for TinyFish and every LLM, so they need no network or keys.
- **Add an LLM provider:** implement `parse(system, prompt, output_format)` and `input_budget` in `services/llm.py`,
  add its settings in `core/config.py`, and wire it into `make_llm()`.
- **Add a source agent:** subclass `BaseAgent` in `agents/`, return `SourceDocument`s, and add it to the agent list
  in `runner.collect()`. Check robots.txt for any new site.
- **Change the API:** edit `schemas/views.py` and the routers, then regenerate the frontend types (§4.6).
- **Change the schema:** update `db/models.py`, add an Alembic migration, and check it with `alembic check`.
- **Privacy:** `backend/fixtures/collected/` holds names and full article text and must never be committed (it is
  git-ignored). Never log private names; progress logs are shown in the UI.

---

## 8. What's left for a complete application

Grouped by area. Within each group, items are listed in rough priority order. Items marked **(brief)** were in
the original project brief and are not built yet.

### Correctness and privacy (do these first)

- **Harden the anonymizer.** Split aliases (`@`, "alias", "a.k.a."), redact first and last names of private
  people on their own, add an NER pass as a second net **(brief: regex + NER + LLM)**, and block saving when a
  registered name survives. Re-anonymize existing cases afterwards.
- **Human review before publishing.** Add a review state for new cases: someone checks the outcome, claims and
  anonymization before a case appears publicly. Allow editing or removing a claim.
- **Extraction accuracy evaluation.** Build a small set of real cases with hand-checked findings and claim
  verdicts, and measure each provider and model against it before trusting scores.
- **Copyright-safe storage.** Store article excerpts and links rather than full article text in the database;
  keep full text only in the local cache, or not at all.
- **Takedown and correction process.** A way for people named in a case, or the court record's owners, to request
  corrections or removal, and an audit log of changes.

### Data coverage

- **A real source of public reactions.** News comment sections are mostly absent. Evaluate sources that allow
  agents (for example YouTube comments on news videos, Mastodon, Lemmy) or licensed social data.
- **Several judgments per case.** Collect the trial court, High Court and Supreme Court judgments, so the timeline
  shows how the outcome changed **(brief: acquittal → media campaign → conviction)**.
- **More news sources.** Add outlet-specific search where Bing News misses coverage, Hindi-language outlets, and
  date filters around key case events **(brief: incident, trial, verdict, appeal)**.
- **eCourts and other judgment sources** besides Indian Kanoon **(brief)**.
- **Hindi and Hinglish sentiment models** (MuRIL or IndicBERT) for reactions **(brief)**.
- **More offence categories**, with category-specific prompts and scoring checks.

### Pipeline and infrastructure

- **A persistent job queue.** Replace in-process jobs with Redis + arq or similar, so jobs survive restarts and
  the API can run as several processes.
- **Streaming progress (SSE)** instead of polling **(brief)**. The backend already has the event log.
- **Cost controls.** A per-case and per-day budget for TinyFish and LLM spend, and refusing jobs once it is
  reached; show the estimated cost before starting.
- **Resume partial collections.** Save each agent's results as they arrive, so a failed run doesn't repeat finished
  TinyFish work.
- **Scheduled refresh** of existing cases to pick up new coverage and later judgments.
- **One database everywhere.** Use Postgres locally too (or a documented way to move cases between local and
  Docker).

### Product features

- **Insights page across cases (brief):** framing distribution, common themes and gap scores across all cases.
- **Separate Judgment, Media and Public tabs (brief),** or deeper drill-down views for each story.
- **Case management:** search and filter cases, re-run or delete a case, see when it was last updated.
- **Shareable reports:** a printable or PDF summary of a case with its evidence.
- **Hindi interface,** at least for labels and the disclaimer.
- **A 3-minute demo script (brief)** and a polished real demo case.

### Security and operations

- **Protect case creation.** `POST /cases` spends money; it needs authentication (an admin login or API key) and
  rate limiting before any public deployment.
- **Deployment:** hosting for the frontend, API and Postgres, HTTPS, secrets management, and backups.
- **Monitoring:** structured logs, error tracking, and alerts for failed jobs and provider errors.
- **CI:** run backend tests, lint, frontend typecheck and lint on every push (for example GitHub Actions).

### Quality

- **Frontend tests:** component tests and an end-to-end test of search → progress → dashboard.
- **Accessibility audit:** keyboard navigation, screen-reader labels for charts, contrast.
- **Load and failure testing:** many jobs at once, provider outages, very long judgments.
