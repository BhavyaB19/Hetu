# Hetu

**One verdict. Three stories. One connected view.**

> Research and education tool. Not legal advice or a predictor. Online opinion is not representative of all
> of India.

## What it is

When a criminal case in India makes the news, three different stories form around it:

1. **The court's story:** what the judgment actually establishes. The facts, motive, trigger, how events
   escalated, and why the court decided as it did.
2. **The media's story:** how news outlets framed it. Headlines, angles, tone, and the factual claims they made.
3. **The public's story:** how people reacted. Which side they leaned towards and which themes kept coming up.

These stories often drift apart. A sudden quarrel gets reported as a "cold-blooded murder", a single blow
becomes "beaten repeatedly", and public anger forms around details the court never found. Hetu puts all three
stories side by side for one case and measures the drift.

## The Perception Gap Index

Each case gets a score from **0** (the media and public narratives match the judgment) to **100** (they have
nothing to do with it). The score is the weighted sum of four components, and the dashboard shows the value,
weight and reason for each one:

| Component | Weight | What it measures |
|---|---|---|
| Factual divergence | 30% | Share of media claims the judgment contradicts (claims it never mentions count half) |
| Framing gap | 25% | How far coverage strays from the court's neutral, procedural frame: share of non-procedural articles and average emotional tone |
| Public sentiment gap | 25% | Share of public reactions that oppose the court's final outcome (neutral and media-bias reactions count half) |
| Timeline distortion | 20% | Gap between how central each event was to the court and how much of the coverage it got |

## Every number has a source

Each finding stores the exact passage it came from. On the dashboard, every fact, claim and timeline event has
a **§ Source** link that opens the quote with its outlet and date. Each media claim is marked *supported*,
*contradicted* or *not in judgment*, with links to both the article passage and the judgment passage.

## How it works

```
TinyFish agents ─► case bundle ─► LLM extraction ─► anonymizer ─► score ─► database ─► dashboard
```

1. **Collection with TinyFish web agents.** Given a case name, two browser agents run in parallel:
   - **JudgmentAgent** works through Indian Kanoon's search results to find the final judgment (the highest
     court's latest decision). The judgment page is then downloaded directly, so its text is exactly as published
     and evidence quotes can be checked word for word.
   - **MediaAgent** searches Bing News, then opens each article in parallel and extracts its full text and any
     reader comments that are publicly visible on the page. Those comments are the public's story. Commenter names
     and handles are never collected.

   Each run has a timeout (a run that overruns is cancelled), retries with backoff on rate limits and server
   errors, and a cap on how many runs go at once. Before any page is visited, its robots.txt is checked, and
   agents are told never to log in, solve CAPTCHAs or get past paywalls. Reddit, Google News and X block automated
   access, so they are not used. The result is a JSON *case bundle*, cached on disk.
2. **Extraction.** An LLM reads each document and returns structured data that is checked against a schema.
   The provider is chosen with `LLM_PROVIDER` (see *Choosing the LLM* below).
   Every quote it cites must appear word for word in the source. If one doesn't, the call is retried with the
   problems listed. Media claims are checked against the judgment in the same step. Judgments can run past
   50,000 words, so each article is checked against only the judgment passages that share the most distinctive
   words with it, and quotes are still verified against the full judgment text.
3. **Anonymization.** Before anything is saved, private individuals (accused, victims, witnesses, relatives,
   minors) are replaced with stable placeholders such as `[VICTIM_1]`. Phone numbers, emails, social handles and
   Aadhaar-style numbers are removed.
4. **Scoring.** The Perception Gap Index is computed from the extracted data.
5. **Dashboard.** A Next.js page shows the score breakdown, timeline, court vs media comparison, public reaction
   and sources.

Collections and extractions are cached, so each case calls TinyFish and the LLM only once (use
`python -m app.cli collect ... --refresh` to collect again). With
`USE_FIXTURES=true`, TinyFish is never called and cached collections are replayed, so a demo works offline.

## Ethics

- Public records and publicly visible content only.
- No individual profiling. Reactions are analysed in aggregate, and no author or handle is ever stored.
- Sentiment is shown as public reaction, never as a judgment of judges.
- No outcome prediction.
- Every extracted claim cites its source.

## Demo case

The repo ships with **Jan Mat v. State**, an *illustrative* criminal-law case: prototype data, not sourced from
a real-world case. It needs no API key and no network.

---

## Setup

### Option 1: Docker (one command)

Docker Desktop must be running.

```bash
docker compose up --build
```

Open http://localhost:3000. This runs Postgres, the API (port 8000) and the frontend, and loads the demo case.

This runs in **development mode** (from `docker-compose.override.yml`, which Compose loads automatically): your
`backend/` and `frontend/` folders are mounted into the containers, and both servers reload when you save a file.
After the first build, `docker compose up` is enough; rebuild with `--build` only when you change dependencies
(`backend/pyproject.toml` or `frontend/package.json`). On Windows, changes are picked up by polling, so allow a
second or two after saving.

For a production-style build with no live reload:

```bash
docker compose -f docker-compose.yml up --build
```

### Option 2: Run locally

Needs Python 3.11+ and Node 20+. The backend uses a local SQLite file, so no database setup is needed.

Backend, from `backend/`:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
python -m app.cli load fixtures/jan-mat-v-state.json
uvicorn app.main:app --reload
```

On macOS or Linux, activate with `source .venv/bin/activate` instead.

Frontend, from `frontend/`:

```bash
npm install
npm run dev
```

Open http://localhost:3000.

### Add a real case

Copy `.env.example` to `.env`, set `TINYFISH_API_KEY`, and set up an LLM provider (see *Choosing the LLM*).

**From the app:** type the case name (and optionally the court) into the search box on the landing page and press
**Analyse**. A progress page shows each stage and a live log of what the agents are doing, then opens the dashboard
when the case is ready. Expect a few minutes.

**From the command line**, from `backend/`:

```bash
python -m app.cli collect "State v. Example" --court "Delhi High Court"
```

This collects the judgment, coverage and comments with TinyFish, then extracts, anonymizes, scores and saves the
case. The raw collection is cached in `backend/fixtures/collected/`, which git ignores because it holds names and
full article text. If extraction fails, load the cached collection again later with
`python -m app.cli load backend/fixtures/collected/<slug>.json`.

To load a bundle you wrote yourself, use `backend/fixtures/jan-mat-v-state.json` as the template, leave out the
`judgment`, `media` and `public` sections, and run `python -m app.cli load path/to/case.json`.

### Choosing the LLM

`LLM_PROVIDER` in `.env` decides which LLM extracts the data. Only that provider is used, and only its key needs to
be set; keys for other providers are ignored. If the chosen provider's key is missing, extraction stops with a
message saying which key to set. The provider and model in use are shown at the start of every extraction log.

| `LLM_PROVIDER` | Key | Default model | Notes |
|---|---|---|---|
| `groq` | `GROQ_API_KEY` | `openai/gpt-oss-120b` (`GROQ_MODEL`) | Set `GROQ_PLAN=developer` on a paid plan. On the free plan (default), long judgments are read in chunks and calls are paced to its ~8,000 tokens per minute: about 20 minutes for a long judgment, and one such case uses much of the free daily allowance. |
| `openai` | `OPENAI_API_KEY` | `gpt-6.1-sol` (`OPENAI_MODEL`) | Whole documents in one call. |
| `anthropic` | `ANTHROPIC_API_KEY` | `claude-opus-5-5` (`ANTHROPIC_MODEL`) | Whole documents in one call. Used when `LLM_PROVIDER` is not set. |

Extractions are cached, so switching provider does not re-extract cases that are already done (run
`python -m app.cli load <file> --extract` to redo one).


## Project structure

```
backend/
  app/
    main.py              FastAPI app: wires routers and the database lifecycle
    cli.py               python -m app.cli: collect a case, or load a case bundle
    agents/              TinyFish web agents
      tinyfish.py          API client: start, poll, cancel, retries, robots.txt check
      judgment.py          JudgmentAgent (finds the judgment on Indian Kanoon)
      indiankanoon.py      reads a judgment page into exact text and metadata
      media.py             MediaAgent (news articles and their public comments)
      runner.py            runs agents in parallel, caches collections
    api/                 HTTP routes
      health.py            GET /health
      jobs.py              POST /cases (start a case), GET /jobs/{id} (progress)
      cases.py             GET /cases, GET /cases/{slug}
    core/
      config.py            settings from .env
    db/
      session.py           engine and sessions
      models.py            tables
      repository.py        save a case, build dashboard views
    schemas/
      bundle.py            case bundle (pipeline input/output) and evidence checks
      extraction.py        what the LLM returns for each extraction call
      views.py             API response models
    services/
      pipeline.py          bundle → extraction → anonymizer → score → database
      jobs.py              background case jobs with a live progress log
      extraction.py        prompts and extractors for judgments, articles, reactions
      llm.py               Groq, OpenAI and Claude clients, rate limiter, validate-and-retry loop
      anonymizer.py        names to placeholders, contact details removed
      scoring.py           Perception Gap Index
  alembic/               migrations
  fixtures/              demo case
  tests/
frontend/
  src/app/           landing page and case dashboard
  src/components/    dashboard sections
  src/lib/           typed API client (generated from OpenAPI) and formatting
```

## API

| Method | Path | Returns |
|---|---|---|
| GET | `/health` | API and database status |
| GET | `/cases` | All cases with their gap score |
| GET | `/cases/{slug}` | Everything the dashboard shows for one case |
| POST | `/cases` | Start collecting and analysing a case `{name, court?}`; returns a job |
| GET | `/jobs/{id}` | Job status (`collecting`, `analysing`, `done`, `failed`) and its live log |

Interactive docs: http://localhost:8000/docs. After changing backend schemas, regenerate the frontend types with
`python backend/scripts/export_openapi.py`, then `npm --prefix frontend run gen:api`.

## Tests

```bash
cd backend && pytest && ruff check .
cd frontend && npm run typecheck && npm run lint
```

Tests cover the TinyFish client and agents (against a fake TinyFish server), the anonymizer (including adversarial
inputs), extraction validation and retries, the gap score, and the API.

## Not in this MVP

- A cross-case Insights page.
- Dedicated Hindi and Hinglish sentiment models (MuRIL or IndicBERT). The LLM handles mixed-language text for now.
