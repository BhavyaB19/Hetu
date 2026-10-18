# Hetu: Architecture v2 (old to new)

How to read this: section 1 is what exists, section 2 is the target, section 3 is the change table with "how to change" for each item, then data model, APIs, jobs, frontend, animation, performance, dependencies, environment and a migration order. Read together with `PRD.md` and `RULES.md`.

---

## 1. Current state (v1), in brief

- **Backend**: FastAPI, async SQLAlchemy, Alembic, SQLite locally / Postgres in Docker.
- **Collection**: TinyFish agents (`JudgmentAgent` on Indian Kanoon, `MediaAgent` on Bing News plus article pages), run in parallel by `agents/runner.py`, cached as case bundles in `fixtures/collected/`.
- **Pipeline**: `services/pipeline.py` runs LLM extraction, anonymization, then the Perception Gap Index, then saves.
- **LLM providers**: Groq, OpenAI, Anthropic, chosen by `LLM_PROVIDER`. The Groq free plan forces chunking and token pacing, which is why a case takes 40 to 50 minutes.
- **API**: `/health`, `/cases`, `/cases/{slug}`, `POST /cases` (public, starts a job), `/jobs/{id}`.
- **Frontend**: Next.js 15, React 19, Tailwind 4. Landing page is a case-search box plus a case list; progress page polls job logs; dashboard shows one case.
- **Gaps**: no ongoing-case tracking, no polls or comments, no cross-case insights page, no animation, jobs in memory, public endpoint can spend money, two databases (SQLite vs Postgres).

Why it "feels like a chatbot": the first thing a visitor sees is an input box that starts a long job and a live log. v2 removes that.

## 2. Target state (v2)

```
Browser (Next.js 15)
 Home | Live Docket | Verdicts | Jan Mat | Motive Atlas | Methodology | Admin
   |  server-side fetch + TanStack Query (client)           ^ SSE (live votes)
   v                                                         |
FastAPI  --------------------------------------------------------------
 public API: home, docket, verdicts, polls/votes/comments, insights
 admin API (ADMIN_API_KEY): add case, review, moderation, jobs
 moderation service  | voter identity service | rate limiting
   |                              |
Postgres (single DB)          Redis (queue + rate limits + SSE fan-out)
   ^                              ^
 arq workers + cron <-------------+
   |- case_ingest job: TinyFish agents -> LLM extraction -> anonymizer -> scoring -> save (draft)
   |- docket_refresh job (daily): TinyFish agents -> hearings
   |- comment_label job: async stance/theme labelling
External: TinyFish Agent API, Indian Kanoon, news sites, LLM provider (paid)
```

Principles:
1. **Public requests only read the database.** Ingestion is always a background job.
2. **Everything is a draft until reviewed.** Public pages show `review_state = published`.
3. **One database, one queue** across local and Docker.
4. **Evidence stays attached** (Span quotes) for every number on screen.

## 3. Change table: old to new, and how to change it

| # | Area | Old (v1) | New (v2) | How to change |
|---|---|---|---|---|
| 1 | Entry point | Landing = search box that starts a job | Landing = animated hero, featured cases, poll of the week, docket ticker | Rewrite `app/page.tsx`; move search into a header filter that only queries existing content; remove job-start UI from public pages |
| 2 | Case creation | Public `POST /cases` | Admin-only `POST /admin/cases` (key + rate limit) | Add `api/admin.py` with an `ADMIN_API_KEY` dependency; remove or 404 the public route; move the job-progress UI under `/admin/jobs/[id]` |
| 3 | Case state | No states | `status` (ongoing/decided), `review_state` (draft/reviewed/published) | Alembic `0002`; `repository.list_cases()` returns published only; admin gets all |
| 4 | Ongoing cases | None | `hearings` table, Live Docket pages, `docket_refresh` job | New `DocketAgent` in `agents/docket.py`; new `services/docket.py`; new routes and pages (section 6, 7) |
| 5 | Public opinion | Scraped comments only (thin) | First-party polls, votes, comments with moderation, SSE results | New tables, `api/polls.py`, `services/moderation.py`, `services/voter.py`; keep scraped reactions as a separate, labelled source |
| 6 | Scoring | Public gap uses scraped reactions | Blend first-party votes and scraped reactions, both labelled | Extend `scoring.py` with `public_sentiment_gap(votes, reactions, w_first_party=0.6)`; store component source counts in the explanation |
| 7 | Cross-case insights | Not built | `/insights/*` endpoints and Motive Atlas page | New `services/insights.py` aggregating published cases; add charts |
| 8 | Routes | `/cases/[slug]` | `/verdicts/[slug]` (+ redirect from `/cases/...`) | Rename route folder; add `redirects()` in `next.config.ts` |
| 9 | Jobs | In-process asyncio, lost on restart | Redis + arq, cron for refresh | Replace `services/jobs.py` `start_job()` with `enqueue()`; add `worker.py`; add Redis to Docker Compose |
| 10 | DB | SQLite local, Postgres Docker | Postgres everywhere | Add `docker compose up db` to the README dev flow; set `DATABASE_URL`; drop SQLite default |
| 11 | LLM speed | Default Groq free plan path, 40 to 50 min | Paid provider default; offline seeding | Set `LLM_PROVIDER=anthropic` (or OpenAI); `GROQ_PLAN=developer` if Groq; see section 9 |
| 12 | Anonymizer | LLM-listed names only, misses aliases | Aliases, first/last name redaction, NER net, save blocked on leakage; also applied to comments | Implement the planned fixes; add `anonymize_text(text, registry)` used by the comment pipeline |
| 13 | Frontend visuals | Static dark theme | Design system plus scroll/page animation plus Lady Justice | Add dependencies (section 10); new `components/motion/*` |
| 14 | Auth | None | Anonymous signed voter id; admin key | Cookie `hetu_voter` (UUID, signed), `voter_hash = HMAC(secret, uuid)` |
| 15 | Rate limiting | None | Per-IP and per-voter limits | `slowapi` with Redis storage; stricter on vote/comment/report |
| 16 | Tests | Backend only | Backend plus Vitest, Playwright, axe | Add suites per RULES.md |

## 4. Data model changes (Alembic `0002_living_platform.py`)

**cases** (add columns)
- `status` enum `ongoing | decided` (default `decided`)
- `review_state` enum `draft | reviewed | published` (default `draft`; set existing demo and collected cases to `published` after review)
- `featured` bool default false
- `decided_on` date null
- `next_hearing_on` date null
- `stage` text null (for ongoing: investigation, trial, arguments, judgment_reserved, appeal)

**hearings**
- `id`, `case_id` FK, `hearing_date` date, `stage` text, `summary` text (neutral, 1 to 3 sentences), `source_url`, `source_name`, `observed_at` timestamptz, unique(`case_id`, `hearing_date`, `source_url`)

**polls**
- `id`, `case_id` FK unique, `question` text, `status` enum `open | closed`, `opens_at`, `closes_at` null, `featured` bool
- Constraint: a poll can be created only if `cases.status = 'decided'` and `review_state = 'published'`.

**votes**
- `id`, `poll_id` FK, `choice` enum `agree | partial | disagree`, `reasons` JSON (array of enum strings), `voter_hash` text, `created_at`, `updated_at`
- Unique (`poll_id`, `voter_hash`).

**comments**
- `id`, `poll_id` FK, `parent_id` FK null (max depth 1), `handle` text, `body` text (post-anonymization), `status` enum `visible | held | removed`, `hold_reason` text null, `stance` enum `agree | disagree | neutral` null, `themes` JSON null, `upvotes` int default 0, `voter_hash`, `created_at`

**comment_votes**: `comment_id`, `voter_hash`, unique pair.

**reports**: `id`, `comment_id`, `voter_hash`, `reason`, `created_at`, unique (`comment_id`, `voter_hash`).

**corrections**: `id`, `case_id` null, `kind` enum `correction | takedown | other`, `message`, `contact` null (stored; never displayed), `status`, `created_at`.

Keep `public_reactions` as the scraped-source table. Do not merge it into `comments`.

Indexes: `votes(poll_id)`, `comments(poll_id, status, created_at)`, `hearings(case_id, hearing_date desc)`, `cases(status, review_state, featured)`.

## 5. API additions

Public (read-only, cacheable) unless noted:
- `GET /home` : featured cases, poll of the week, ticker items, counters
- `GET /docket?court=&category=&stage=&sort=` and `GET /docket/{slug}` (hearings, coverage)
- `GET /verdicts?court=&category=&year=&gap_min=&gap_max=` and `GET /verdicts/{slug}` (existing case view; keep `/cases/*` as an alias for one release)
- `GET /polls?sort=trending|new|divided` and `GET /polls/{id}`
- `POST /polls/{id}/vote` (body: choice, reasons) , `GET /polls/{id}/results`, `GET /polls/{id}/stream` (SSE)
- `GET /polls/{id}/comments?sort=top|new` , `POST /polls/{id}/comments`, `POST /comments/{id}/upvote`, `POST /comments/{id}/report`
- `GET /insights/overview`, `/insights/motives`, `/insights/escalation`, `/insights/outlets`, `/insights/sankey`
- `POST /corrections`

Admin (header `X-Admin-Key`):
- `POST /admin/cases` {name, court, category, status}, `GET /admin/jobs`, `GET /admin/jobs/{id}`
- `GET /admin/cases/{slug}/preview`, `PATCH /admin/cases/{slug}` (review_state, featured), `PATCH /admin/claims/{id}` (edit/remove)
- `GET /admin/moderation`, `POST /admin/comments/{id}/approve|remove`, `POST /admin/polls` (create from a published decided case)

After any change to `schemas/views.py`: `python backend/scripts/export_openapi.py` then `npm --prefix frontend run gen:api`. Never edit `schema.d.ts` by hand.

## 6. Backend services to add

- `services/voter.py`: reads or sets the signed `hetu_voter` cookie, returns `voter_hash`. Cookie: HttpOnly, SameSite=Lax, 1 year. Hash IP only for rate-limit keys, never store raw IPs.
- `services/polls.py`: vote upsert, results aggregation (counts, percentages, reason tallies), trending score = recent votes weighted by recency, divided score = closeness of agree vs disagree.
- `services/moderation.py`: pipeline from PRD section 7 as small, testable functions: `validate`, `strip_pii`, `mask_registered_names`, `abuse_check`, `contempt_check`, returning `(status, hold_reason, cleaned_body)`.
- `services/docket.py`: merges new hearing observations, computes `stage` and `next_hearing_on`, writes `hearings`.
- `services/insights.py`: SQL aggregates over published cases; cache results in memory for 60 s.
- `agents/docket.py` (TinyFish): see section 7.
- `worker.py` (arq): `case_ingest`, `docket_refresh` (cron), `comment_label`.

## 7. Docket ingestion with TinyFish

`DocketAgent` flow per ongoing case:
1. **Find sources**: agent searches news (same safe approach as `MediaAgent`) for the case name plus "hearing" within the last 30 days; returns up to N article URLs.
2. **Extract hearing facts**: per article, goal "return the most recent hearing date, the court, the stage, what was decided or adjourned, and the next hearing date, each only if stated". Use an `output_schema`; empty fields stay null.
3. **Official check (optional)**: if a court's public cause-list page allows automated access (robots.txt), a second agent confirms the date. If blocked, skip.
4. **Neutral summary**: LLM writes a 1 to 3 sentence neutral summary from extracted facts only; a rule forbids adjectives about guilt or evidence strength.
5. **Upsert** into `hearings`; update `cases.next_hearing_on` and `stage`.
Schedule: daily cron plus an admin "refresh now" button. Show `observed_at` on every card. Respect `TINYFISH_CONCURRENCY` and per-day budget.

## 8. Frontend structure (changes)

```
frontend/src/app/
  page.tsx                  Home (hero + sections)
  docket/page.tsx           Live Docket list
  docket/[slug]/page.tsx    Docket detail
  verdicts/page.tsx         Library
  verdicts/[slug]/page.tsx  Case dashboard (moved from cases/[slug])
  jan-mat/page.tsx          Poll index
  jan-mat/[pollId]/page.tsx Poll page
  atlas/page.tsx            Motive Atlas
  methodology/page.tsx
  admin/...                 cases, jobs, review, moderation
  api/                      server-side proxies (keep pattern)
frontend/src/components/
  motion/ ScalesHero.tsx, LadyJusticeReveal.tsx, PageTransition.tsx, CountUp.tsx, Reveal.tsx, DrawLine.tsx, Marquee.tsx
  docket/ DocketCard.tsx, StageBadge.tsx, HearingTimeline.tsx
  jan-mat/ PollCard.tsx, VoteWidget.tsx, ResultsBars.tsx, CommentThread.tsx, CommentForm.tsx, ThreeWayGauge.tsx
  atlas/ MotiveBars.tsx, EscalationLadder.tsx, SankeyChart.tsx, OutletFraming.tsx
  ui/ (shadcn components)
```

Design tokens live in `globals.css` as CSS variables (`--color-bg`, `--color-ink`, `--color-gold`, `--color-viz-1..4`); do not hard-code hex values in components.

### Animation implementation (Anime.js v4)

**Verified Package & Imports**: Installed `animejs@4.5.0`. TypeScript exports verified from `dist/modules/index.d.ts`:
- Core & Timeline: `import { animate, createTimeline, createScope } from 'animejs';`
- Spring Physics: `import { spring, createSpring } from 'animejs';` (both are exported and identical in `animejs@4.5.0`)
- SVG Drawing: `import { createDrawable, morphTo, createMotionPath, svg } from 'animejs';` (`createDrawable` is exported both as a bare function and on the `svg` namespace: `svg.createDrawable()`)
- Draggable & Events: `import { createDraggable, onScroll, stagger, utils } from 'animejs';`

**Scales hero (P0): layered SVG + CSS 3D.** Build `ScalesHero` from an SVG with groups `#base`, `#beam`, `#pan-left`, `#pan-right`. Beam sways with a gentle sine oscillation via Anime.js (`animate(beam, { rotate: [-3, 3], loop: true, alternate: true, ease: 'inOutSine', duration: 3000 })`). Y-axis spin uses CSS `perspective` and `rotateY` on a wrapper; front and back art layers maintain `backface-visibility: hidden`.

**Lady Justice reveal (P0): Anime.js timeline.**
- Assets: `public/art/lady-front.svg` (with `<g id="blindfold">`), `public/art/lady-back.svg`.
- Anime.js timeline (`createTimeline`): `rotateY: [0, 360]` (2000 ms, `inOutQuad`); at 1600 ms animate `#blindfold` (`translateX: 40, rotate: 25, opacity: 0, duration: 600`) and fade in eyes; then stagger page content with `stagger(100)`.
- Persist `sessionStorage.hetuReveal = "1"`; skip button; `prefers-reduced-motion` renders the end state immediately.
- Encapsulated in `createScope({ root })` with cleanup via `scope.revert()`.

**Live Scales of Public Opinion (P1): Spring-driven data visualization.**
- SVG balance scale where Agree votes lower the left pan and tilt the beam counter-clockwise; Disagree votes lower the right pan; Partly Agree splits evenly.
- Tilt angle: `ratio = total > 0 ? (effectiveAgree - effectiveDisagree) / total : 0`.
- Zero votes: sits level (0° tilt) with the label "No votes yet".
- Below 10 votes: tilt angle is capped proportionally so a handful of early votes cannot cause a dramatic swing.
- Idle sway: gentle sine oscillation runs only when `prefers-reduced-motion` is off.
- When new votes arrive (SSE or poll response), animate rotation and pan `translateY` using `spring({ bounce: 0.35, duration: 800 })`.
- Optional vote token uses `createDraggable(tokenRef, { container, onRelease })`. Hidden when `(pointer: coarse)` matches (mobile/touch); tap buttons are the primary control everywhere.

**3D upgrade (P1): React Three Fiber.** Load a compressed GLB (under 3 MB, Draco) with `useGLTF`; wrap in `<Canvas dpr={[1,1.5]}>`, `<Environment preset="city" />`, slow `useFrame` rotation. Requirements for the asset: license verified (CC0 or CC-BY with attribution in Methodology), and a separate mesh named `Blindfold` animated via Anime.js Three.js adapter or R3F `useFrame`. Load with `next/dynamic({ ssr:false })`; gate behind `NEXT_PUBLIC_ENABLE_3D` and capability checks. If no suitable model exists, keep the SVG version.

**Scroll motion**: Anime.js `onScroll({ sync: true, target, enter, leave })` for scrubbed timelines and SVG stroke drawing via `createDrawable()`. For pinned scenes on Home (Court, Media, Public), utilize standard CSS `position: sticky` with top offset tracks. Smooth scrolling with Lenis is removed; native browser scrolling is used everywhere.

## 9. Performance and ingestion fixes (the 40 to 50 minute problem)

Root causes: Groq free-plan token limits (about 4,500 tokens per request and 7,500 per minute) force map-reduce chunking and sleeps.

Fixes, in order of impact:
1. **Use a paid provider for ingestion.** Default `LLM_PROVIDER=anthropic` (or OpenAI). With a large context window, judgments up to the model's limit can be extracted in one structured call instead of chunk, select, final. Keep the chunked path only for oversized documents.
2. **Parallelize article extraction** with a semaphore (for example 4 at a time) instead of serial calls; keep the `TokenRateLimiter` per provider.
3. **Cache aggressively**: judgment checkpoint, extracted bundle (already present), and a hash-based cache for article extractions.
4. **Seed offline, serve instantly**: add `python -m app.cli seed seeds/cases.yaml --concurrency 2` that ingests a list of cases (name, court, category, status) and stores them as drafts. Run it the night before the demo; review and publish in the admin.
5. **Never expose job progress to the public.** Only admins see `/admin/jobs/[id]`.
6. **Budget guard**: `MAX_DAILY_LLM_USD` and `MAX_DAILY_AGENT_RUNS`; refuse new jobs when exceeded; log estimated cost per job.
Target: under 15 minutes per case on a paid provider; public page loads under 1 s from the database.

## 10. Dependencies (approved list)

Frontend: `shadcn/ui` (Radix primitives), `class-variance-authority`, `clsx`, `tailwind-merge`, `lucide-react`, `framer-motion`, `animejs` (^4.5.0), `three`, `@react-three/fiber`, `@react-three/drei` (P1), `recharts` plus `d3-sankey`, `@tanstack/react-query`, `zod`, `react-hook-form`, `sonner`, `next-intl` (P1, Hindi). Testing: `vitest`, `@testing-library/react`, `@playwright/test`, `@axe-core/playwright`.

Backend: `arq`, `redis`, `slowapi`, `sse-starlette`, `pyyaml`, `better-profanity` (plus a custom Hindi/Hinglish list file), `structlog`, `pytest-asyncio`. Optional: `sentry-sdk`.

Dev tooling: ESLint, Prettier, Ruff, `pre-commit`.

Adding anything outside this list requires a note in the PR describing why.

## 11. Environment additions

`ADMIN_API_KEY`, `VOTER_HASH_SECRET`, `REDIS_URL`, `DATABASE_URL` (Postgres), `DOCKET_REFRESH_CRON` (default `0 6 * * *`), `MAX_DAILY_LLM_USD`, `MAX_DAILY_AGENT_RUNS`, `COMMENT_RATE_LIMIT`, `NEXT_PUBLIC_ENABLE_3D` (default `false`), `NEXT_PUBLIC_SITE_URL`.

Docker Compose: add `redis` and a `worker` service (same image as backend, command `arq app.worker.WorkerSettings`). Keep the dev override with mounted source.

## 12. Security and privacy checklist
- Public endpoints cannot start jobs or spend money.
- Admin key compared in constant time; never logged.
- Cookies signed; votes and comments store `voter_hash`, not IP.
- Comment bodies stored post-anonymization only.
- CORS limited to the site origin; security headers (CSP allowing only needed script hosts).
- `fixtures/collected/` stays git-ignored; no private names in logs.
- Store article excerpts and links in the database, not full article text (copyright); full text only in the local cache.

## 12b. Testing additions
Backend: poll uniqueness and vote change, comment pipeline edge cases (PII, Hindi abuse list, held states), polls blocked for ongoing cases, docket upsert idempotency, insights aggregates, admin auth. Frontend: component tests for VoteWidget and CommentThread, Playwright flows (home to poll, vote, comment, see results), axe checks on every page, reduced-motion test for the reveal.

## 13. Migration order (safe path from v1)
1. Switch to Postgres locally; confirm demo case loads.
2. Run Alembic `0002`; mark the demo and the reviewed collected cases `published`.
3. Add admin API and move creation there; delete the public route.
4. Ship polls, votes, comments, moderation (backend then UI).
5. Ship docket agent, cron, seeds, then UI.
6. Rename routes to `/verdicts` with redirects.
7. Add insights endpoints and Atlas page.
8. Add the design system and animations last on top of working pages.
9. Seed and review content; run full test suites; deploy.