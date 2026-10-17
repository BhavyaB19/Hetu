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
case bundle (JSON) ─► Claude extraction ─► anonymizer ─► score ─► database ─► dashboard
```

1. **Input.** A case is a JSON *bundle*: the final judgment, news articles and public reactions as plain text.
2. **Extraction.** Claude reads each document and returns structured data that is checked against a schema.
   Every quote it cites must appear word for word in the source. If one doesn't, the call is retried with the
   problems listed. Media claims are checked against the judgment in the same step.
3. **Anonymization.** Before anything is saved, private individuals (accused, victims, witnesses, relatives,
   minors) are replaced with stable placeholders such as `[VICTIM_1]`. Phone numbers, emails, social handles and
   Aadhaar-style numbers are removed.
4. **Scoring.** The Perception Gap Index is computed from the extracted data.
5. **Dashboard.** A Next.js page shows the score breakdown, timeline, court vs media comparison, public reaction
   and sources.

The extracted bundle is saved next to the input file, so a case only calls the API once.

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

### Option 2: Run locally

Needs Python 3.11+ and Node 20+. The backend uses a local SQLite file, so no database setup is needed.

Backend, from `backend/`:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
python -m app.cli fixtures/jan-mat-v-state.json
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

1. Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`.
2. Write a bundle with one judgment, plus any articles and reactions. Use `backend/fixtures/jan-mat-v-state.json`
   as the template and leave out the `judgment`, `media` and `public` sections.
3. Run `python -m app.cli path/to/case.json` from `backend/`. It extracts, anonymizes, scores and saves the
   case, and writes `case.extracted.json` next to the input.

## Project structure

```
backend/
  app/
    main.py              FastAPI app: wires routers and the database lifecycle
    cli.py               python -m app.cli: load case bundles into the database
    api/                 HTTP routes
      health.py            GET /health
      cases.py             GET /cases, GET /cases/{slug}
    core/
      config.py            settings from .env
    db/
      session.py           engine and sessions
      models.py            tables
      repository.py        save a case, build dashboard views
    schemas/
      bundle.py            case bundle (pipeline input/output) and evidence checks
      extraction.py        what Claude returns for each extraction call
      views.py             API response models
    services/
      pipeline.py          bundle → extraction → anonymizer → score → database
      extraction.py        prompts and extractors for judgments, articles, reactions
      llm.py               Claude client, validate-and-retry loop
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

Interactive docs: http://localhost:8000/docs. After changing backend schemas, regenerate the frontend types with
`python backend/scripts/export_openapi.py`, then `npm --prefix frontend run gen:api`.

## Tests

```bash
cd backend && pytest && ruff check .
cd frontend && npm run typecheck && npm run lint
```

Tests cover the anonymizer (including adversarial inputs), extraction validation and retries, the gap score, and
the API.

## Not in this MVP

- Live collection of judgments, news and reactions with TinyFish web agents. Cases are loaded from bundles for now.
- Starting a new case from the UI, with live pipeline progress.
- A cross-case Insights page.
- Dedicated Hindi and Hinglish sentiment models (MuRIL or IndicBERT). Claude handles mixed-language text for now.
