# Hetu: Antigravity Prompts

How to use:
1. Put `AGENTS.md` (copy of `RULES.md`), `PRD.md`, `ARCHITECTURE.md` and this file in the repo root, next to the existing code.
2. Run prompts **in order**, one per conversation/task. Review the plan before approving code (use review/planning mode).
3. After each prompt, run the checks listed and commit. Do not start the next prompt on a red build.
4. If the agent drifts, paste the **Correction prompt** at the bottom.

Every prompt below assumes the agent has read `AGENTS.md`, `PRD.md` and `ARCHITECTURE.md`. Each ends with acceptance criteria you can check yourself.

---

## Prompt 0: Audit and plan (no code changes)

```text
Read AGENTS.md, PRD.md and ARCHITECTURE.md fully. Then audit the existing repo (backend/ and frontend/) against ARCHITECTURE.md section 3.

Deliver ONE file, IMPLEMENTATION_PLAN.md, containing:
1. What already exists and can be reused as is.
2. What must change, mapped to the 16 rows of the change table.
3. A phased task list matching PRD.md section 11, with estimated effort (S/M/L) and dependencies.
4. Risks, assumptions and open questions (max 10) for me to answer.
5. A list of any contradictions between the three docs and the code.

Constraints: do NOT modify any code or config. Do NOT install packages. If something in the docs is ambiguous, list it as a question instead of choosing silently.

Acceptance: IMPLEMENTATION_PLAN.md exists; no other file changed (git status clean apart from that file).
```

## Prompt 1: Postgres everywhere, data model and migrations

```text
Implement ARCHITECTURE.md sections 3 (rows 3 and 10) and 4.

Tasks:
1. Make Postgres the default for local development: update docker-compose so `docker compose up db` works, set `.env.example`, update README setup. Remove the SQLite default.
2. Add models and Alembic migration `0002_living_platform` for: new `cases` columns (status, review_state, featured, decided_on, next_hearing_on, stage), and new tables hearings, polls, votes, comments, comment_votes, reports, corrections, with the constraints and indexes in section 4. Include a database-level check that a poll can only exist for a decided, published case (trigger or constraint plus service-level validation).
3. Update `db/repository.py`: list and get queries return only `review_state = published` for public functions; add admin variants that return everything.
4. A data migration that sets existing demo and collected cases to `status = decided` and `review_state = published`.
5. Tests for constraints (unique vote per poll and voter, poll only on decided published case, comment depth max 1).

Constraints: reversible migration; do not change existing column names; do not touch the pipeline logic yet.

Acceptance: `alembic upgrade head` and `alembic downgrade -1` both succeed on a fresh Postgres; `pytest` and `ruff check .` pass; the existing demo case still loads and renders.
```

## Prompt 2: Admin API, remove public job creation

```text
Implement ARCHITECTURE.md section 3 row 2 and the admin part of section 5.

Tasks:
1. Add `api/admin.py` protected by an `X-Admin-Key` header compared in constant time to `ADMIN_API_KEY`. Never log the key.
2. Move case creation to `POST /admin/cases` (name, court, category, status). Remove or return 404 for the public `POST /cases`. Keep `GET /jobs/{id}` only under `/admin/jobs/{id}`.
3. Add `PATCH /admin/cases/{slug}` for review_state and featured, and `GET /admin/cases/{slug}/preview`.
4. Add rate limiting with slowapi (Redis storage configurable; fall back to in-memory only when REDIS_URL is unset in dev).
5. Frontend: remove job-start UI from public pages; create minimal `/admin` pages (cases list, add case, job progress) that call the backend through server-side proxies so the key never reaches the browser.

Acceptance: public requests to admin routes return 401/403; a case added in admin appears as draft and is invisible on public pages until published; tests cover auth and visibility; frontend typecheck/lint pass.
```

## Prompt 3: Polls, votes, comments and moderation (backend)

```text
Implement PRD.md sections 5.4 and 7, and ARCHITECTURE.md sections 5 and 6 for polls.

Tasks:
1. `services/voter.py`: signed anonymous cookie `hetu_voter`, `voter_hash` via HMAC with VOTER_HASH_SECRET.
2. `services/polls.py` and routes: list polls (sort trending/new/divided), get poll, vote (upsert), results (counts, percentages, reason tallies), SSE stream `/polls/{id}/stream` (falls back to 10s polling if SSE not available).
3. Comments: create, list (top/new), one-level replies, upvote, report. Auto-generate anonymous handles.
4. `services/moderation.py` with small pure functions: validate (3 to 800 chars), strip_pii (reuse anonymizer regexes), mask_registered_names, abuse_check (English plus a Hindi/Hinglish wordlist file at backend/app/data/abuse_terms.txt that you create with a conservative starter list and clearly mark as needing human review), contempt_check (threats/calls for violence, personal attacks on judges). Output: (status, hold_reason, cleaned_body).
5. Three reports auto-hide a comment (status held).
6. Reject votes/comments on polls whose case is not decided and published.
7. Rate limits: 5 comments/hour/voter, 30 votes/hour/voter, per-IP caps.
8. Admin moderation endpoints: list held/reported, approve, remove.

Constraints: store voter_hash only, never raw IP; never log comment bodies; no auto-delete.

Acceptance: pytest covers every moderation branch, duplicate vote handling, vote change, rate limiting, poll-on-ongoing-case rejection, SSE basic test; OpenAPI regenerated and frontend types regenerated.
```

## Prompt 4: Docket ingestion with TinyFish and scheduling

```text
Implement ARCHITECTURE.md section 7 and the docket parts of sections 4 to 6, and the queue in row 9.

Tasks:
1. Add Redis and a `worker` service to docker-compose; implement `app/worker.py` with arq: jobs `case_ingest`, `docket_refresh` (cron from DOCKET_REFRESH_CRON), `comment_label`. Replace the in-memory `start_job()` with `enqueue()`; jobs must be idempotent and survive restarts.
2. `agents/docket.py` (`DocketAgent`) built on the existing `tinyfish.py` client and robots.txt checks. Flow: find recent hearing coverage, extract {hearing_date, court, stage, outcome_or_adjournment, next_hearing_date} with an output_schema (null when not stated), optionally confirm with an official cause-list page only if robots.txt allows.
3. `services/docket.py`: neutral summary generation (LLM; facts only; no adjectives about guilt or evidence), upsert into `hearings`, update `cases.next_hearing_on` and `stage`.
4. Public endpoints `GET /docket` (filters/sorts) and `GET /docket/{slug}`.
5. CLI: `python -m app.cli docket-refresh [--slug X]`.
6. A fake DocketAgent for tests (no network).

Constraints: respect TINYFISH_CONCURRENCY and daily run budget; cancel remote runs on timeout; log readable steps with no private names.

Acceptance: refresh job is idempotent (running twice creates no duplicates); tests pass with fakes; a manual `docket-refresh` with TINYFISH_API_KEY set fills hearings for a seeded ongoing case; every hearing has source_url.
```

## Prompt 5: Design system and app shell

```text
Implement PRD.md sections 4 and 6.1 and ARCHITECTURE.md section 8 (structure only, no heavy animation yet).

Tasks:
1. Install and configure the approved frontend dependencies for UI: shadcn/ui (Radix), class-variance-authority, clsx, tailwind-merge, lucide-react, sonner, next-themes is NOT needed (dark only).
2. Define design tokens in globals.css (background, ink, gold, muted, borders, four viz colours, radius, spacing, shadows). Playfair Display, Manrope, plus a Devanagari font via next/font.
3. Build the app shell: header with logo, nav (Home, Live Docket, Verdicts, Jan Mat, Motive Atlas, Methodology), a content filter/search that queries existing content only, mobile bottom bar or drawer, footer with disclaimer links, global disclaimer banner.
4. Create shared components: Card, Badge/StageBadge, Stat, SectionHeader, Skeleton variants, EmptyState, ErrorState, DataTable.
5. Create placeholder routes for /docket, /verdicts, /jan-mat, /atlas, /methodology with the shell and skeletons. Add redirects from /cases/* to /verdicts/*.

Constraints: no hard-coded hex values in components; keyboard accessible; works at 375/768/1280 widths.

Acceptance: typecheck/lint pass; every nav link works; Lighthouse accessibility score of at least 95 on placeholder pages; screenshots of 3 breakpoints attached to the change summary.
```

## Prompt 6: Home page and scales animation

```text
Implement PRD.md sections 5.1 and 6.2 and ARCHITECTURE.md section 8 (scales hero P0).

Tasks:
1. `GET /home` endpoint (featured cases, poll of the week, ticker items, counters) if not present, with a typed response.
2. `components/motion/ScalesHero.tsx`: layered SVG scales (groups #base, #beam, #pan-left, #pan-right). Slow Y-axis rotation with CSS 3D (perspective + rotateY, front and back art layers with backface-visibility hidden), beam sway with Anime.js inOutSine, pan counter-sway, subtle mouse parallax. Create original vector art in `public/art/` (simple, elegant, gold on dark).
3. Home sections: hero + CTAs, three-story scroll section (Court, Media, Public) using modern CSS `position: sticky` runways synchronized via Anime.js `onScroll({ sync: true })`, featured cases carousel, poll of the week card, docket ticker (pausable marquee), live counters with count-up.
4. Skeletons while data loads; graceful empty states if there is no data.
5. Respect prefers-reduced-motion everywhere via `createScope({ mediaQueries })`; lazy-load heavy motion code; pause animations when the tab is hidden (`document.hidden`). Clean up via `scope.revert()`.

Constraints: animate transform/opacity only; do not add React Three Fiber yet; no search box as the hero element.

Acceptance: Home is usable with animations disabled; LCP under 2.5s locally; no console errors; reduced-motion test in Playwright passes; Anime.js scopes are cleaned up via `scope.revert()` on route change.
```

## Prompt 7: Live Docket UI

```text
Implement PRD.md section 5.2.

Tasks:
1. `/docket` list: DocketCard (title, court, category, StageBadge, next hearing date, last-updated, 2 to 3 line summary), filters (court, category, stage, hearing this week), sort (next hearing, most covered, recently updated), URL-synced filters, staggered reveal.
2. `/docket/[slug]`: hearing history timeline (line draws on scroll via Anime.js `createDrawable` + `onScroll`), media coverage feed (outlet, date, headline, link, framing tag), "key questions before the court" bullets (neutral), Follow button using localStorage, sub judice notice explaining polls open after judgment.
3. Visible "last checked" time on every card and detail page; stale (older than 48h) data shows a subtle warning.
4. No vote or comment UI on ongoing cases.

Acceptance: works with 8+ seeded ongoing cases; filters and sorts correct; keyboard accessible; empty/error/loading states done; Playwright test covers filter -> detail -> follow.
```

## Prompt 8: Jan Mat UI, Lady Justice reveal and Live Scales

```text
Implement PRD.md sections 5.4 and 6.3 and ARCHITECTURE.md section 8 (Lady Justice reveal P0 and Live Scales P1).

Tasks:
1. `/jan-mat` index: poll cards, sort tabs (Trending, Newest, Most divided), pinned Poll of the week.
2. `components/motion/LadyJusticeReveal.tsx`: original layered SVG artwork `public/art/lady-front.svg` (with `<g id="blindfold">`) and `lady-back.svg`. Anime.js timeline (`createTimeline()`, about 3.5s): fade in from behind, rotateY 0 to 360 with inOutQuad, as she returns to face front the blindfold unties (translateX +40, rotate 25, opacity 0), eyes revealed, scales settle, content staggers in (`stagger(100)`), caption "Justice is blind. The public is not." Run once per session (sessionStorage), Skip button, reduced-motion shows the end state, pause on hidden tab. Encapsulate in `createScope` with `scope.revert()`.
3. `components/jan-mat/LiveScales.tsx`: Live Scales of Public Opinion. Interactive SVG balance scale where beam tilt angle and pan heights are driven by the Agree vs Disagree ratio (Partly agree splits 50/50). Animate tilt and pan translateY with `spring({ bounce: 0.35, duration: 800 })` on vote result updates (SSE or polling).
   - Zero votes: level balance (0° tilt) with "No votes yet" label.
   - Small sample protection: below 10 votes, cap the tilt proportionally to prevent wild swings.
   - Idle sway: gentle sine oscillation runs only when `prefers-reduced-motion` is off.
   - Drag token: optional draggable vote token using `createDraggable`. Hide the drag token when `(pointer: coarse)` matches (mobile/touch); tap buttons are the primary control everywhere.
4. `/jan-mat/[pollId]`: plain-language summary, optional "I have read the summary" checkbox (does not block voting), VoteWidget (Agree/Partly/Disagree + reason chips), animated ResultsBars with aria-live updates (SSE with polling fallback), LiveScales widget, "Not a representative sample" notice, CommentThread (anonymous handle, one-level replies, upvote, report, sort Top/Newest), CommentForm with clear moderation messaging ("held for review" state), ThreeWayGauge for Public vs Media vs Court plus the Perception Gap Index.
5. Toasts for success/errors (sonner). Optimistic UI for votes and upvotes with rollback on error.

Constraints: the animation must never block voting or reading; no sounds; keep dignified tone.

Acceptance: vote -> results update -> live scales spring-tilts -> comment -> appears (or held message) works end to end; duplicate vote updates instead of duplicating; axe has no serious violations; reveal skippable and disabled for reduced motion; Playwright flow passes.
```

## Prompt 9: Verdicts refactor (and remove the chatbot feel)

```text
Implement PRD.md section 5.3 and ARCHITECTURE.md section 3 rows 1 and 8.

Tasks:
1. `/verdicts` library: filters (court, category, year, Perception Gap range), cards with gap score and case summary.
2. Move the existing case dashboard to `/verdicts/[slug]`; restyle with the design system; add scroll-driven reveals (timeline draws, gap needle animates, claim verdict bars animate).
3. Add a plain-language summary block at the top and a "Vote on this verdict" card linking to the Jan Mat poll.
4. Keep every Source link and the evidence popover working.
5. Remove any remaining chat-like interaction or job-start UI from public pages; confirm landing has no prompt box.
6. Update scoring: `public_sentiment_gap` blends first-party votes and scraped reactions (w_first_party = 0.6 when at least 20 votes, else scraped only), with explanation text stating the sources and counts. Update tests and fixtures.

Acceptance: old /cases URLs redirect; scoring tests updated and passing; dashboard visually consistent with the design system; no regressions in the demo case.
```

## Prompt 10: Insights API and Motive Atlas page

```text
Implement PRD.md section 5.5 and ARCHITECTURE.md sections 5 and 6 (insights).

Tasks:
1. `services/insights.py` + endpoints `/insights/overview`, `/motives`, `/escalation`, `/outlets`, `/sankey`, with court/year/category filters, computed only over published cases, each response including `n` (sample size). Cache 60 seconds.
2. `/atlas` page with: motive categories bar chart, trigger types, relationship between parties, escalation ladder visualization, offence-to-trigger Sankey (d3-sankey), framing by outlet, Perception Gap distribution. Recharts for standard charts.
3. Every chart: shows `n`, has an accessible data table alternative, supports drill-down to the list of contributing cases, handles tiny samples with a clear message.
4. CSV export of aggregated, anonymized data.

Acceptance: renders with at least 6 seeded cases; charts keyboard-reachable; no private names anywhere; tests for aggregates.
```

## Prompt 11: Review workflow, moderation UI and methodology page

```text
Implement PRD.md sections 5.6 and 5.7.

Tasks:
1. Admin review: preview a draft case (judgment findings, claims, anonymization check), edit or remove a claim, approve -> published. Block publishing if the anonymization leakage check finds a registered private name in any stored text.
2. Admin moderation queue UI for held and reported comments (approve/remove), and corrections inbox.
3. `/methodology` page: Perception Gap Index components and weights (pull explanations from scoring.py so docs and code stay in sync), sources and robots.txt policy, limits, sub judice policy, takedown/correction form posting to `/corrections`, third-party asset licenses (attribution list).
4. Harden the anonymizer per ARCHITECTURE.md row 12 (aliases, first/last names, NER net, block-on-leak) and re-run anonymization on existing cases.

Acceptance: a case cannot be published with a leaked registered name (test); moderation actions work; methodology page renders from live scoring explanations.
```

## Prompt 12: Pipeline speed and seeding

```text
Implement ARCHITECTURE.md section 9.

Tasks:
1. Default provider to a paid one via env; remove reliance on Groq free-plan pacing for normal runs (keep it as an option). Add single-call extraction for judgments that fit the model's context; keep chunked path only for oversized documents.
2. Parallelize article extraction with a semaphore (configurable), with per-provider rate limiting.
3. Hash-based cache for article extractions; keep judgment checkpoint and extracted bundle cache.
4. Budget guards: MAX_DAILY_LLM_USD and MAX_DAILY_AGENT_RUNS; refuse jobs when exceeded; log estimated cost per job (admin job list shows duration, provider, estimated cost).
5. `python -m app.cli seed seeds/cases.yaml --concurrency 2`: ingest a YAML list of cases (name, court, category, status) as drafts; create `seeds/cases.example.yaml` with clearly marked placeholders (do NOT invent real case facts).
6. Benchmark script that prints time per stage for one case.

Acceptance: a benchmark run on the Jessica Lal bundle shows total ingestion time (report it honestly, with provider and model); seeding two cases concurrently works; budget guard test passes.
```

## Prompt 13: Quality, accessibility and polish

```text
Complete testing and polish.

Tasks:
1. Add Vitest + Testing Library component tests for VoteWidget, CommentThread, ResultsBars, DocketCard.
2. Add Playwright end-to-end tests: Home -> Live Docket -> detail -> follow; Verdicts -> vote card -> poll -> vote -> comment; Admin add case (mock job) -> review -> publish.
3. Add @axe-core/playwright checks on every page and fix serious/critical issues.
4. Reduced-motion and keyboard-only passes on Home and Jan Mat.
5. Lighthouse budgets: Performance 85+ on Home (3D off), Accessibility 95+.
6. Add GitHub Actions CI: backend (pytest, ruff), frontend (typecheck, lint, vitest), Playwright smoke.
7. Fix visual inconsistencies against the design system; check 375/768/1280.

Acceptance: CI green; list of known gaps written honestly in KNOWN_GAPS.md.
```

## Prompt 14: Docker and deployment readiness

```text
Prepare deployment.

Tasks:
1. Production docker-compose: db, redis, backend, worker, frontend (standalone Next.js), with healthchecks and restart policies.
2. Environment documentation: `.env.example` complete; separate dev/prod notes; secrets never committed.
3. Security headers and CSP (allow only needed script/style/font hosts), CORS limited to the site origin, cookie flags (HttpOnly, Secure in prod, SameSite=Lax).
4. Backup note for Postgres and a seed/restore procedure.
5. Update README with: local dev, seeding, admin usage, running the worker, how to run tests.

Acceptance: `docker compose -f docker-compose.yml up --build` brings up the full stack; a smoke test passes against it; README steps verified from a clean clone.
```

---

## Optional prompt A: React Three Fiber upgrade (only if you have a licensed GLB)

```text
Add the P1 3D scales/Lady Justice per ARCHITECTURE.md section 8, behind NEXT_PUBLIC_ENABLE_3D (default false).

Inputs: the GLB at public/models/<name>.glb (I will supply it; license: <license>). Required: a mesh named `Blindfold`.

Tasks: load with useGLTF (Draco), Canvas with dpr [1,1.5], Environment preset "city", slow rotation via useFrame, Anime.js Three.js adapter or R3F useFrame for the blindfold reveal on /jan-mat, capability checks (hardwareConcurrency >= 4, not mobile low-end, not reduced-motion), fallback to the SVG version, lazy-load with next/dynamic ssr:false, add the model's attribution to /methodology.

Acceptance: toggling the flag switches implementations; no extra JS on pages where 3D is off; frame rate acceptable on a mid-range laptop; fallback verified.
```

## Optional prompt B: Hindi labels (P1)

```text
Add next-intl with English and Hindi for navigation, buttons, poll question and choices, stage badges and the disclaimer. Do not machine-translate legal text or judgment content; mark any translation that needs human review in a TRANSLATION_REVIEW.md. Language switcher in the header; default English; persist choice in a cookie.

Acceptance: switching language works on all main pages; Devanagari font renders; no layout breakage at 375px.
```

## Correction prompt (paste when the agent drifts)

```text
Stop. You deviated from AGENTS.md / PRD.md / ARCHITECTURE.md. Specifically: <what went wrong>.
1. Do not make further edits yet.
2. List the files you changed and which rule or requirement each change broke.
3. Propose the smallest set of changes to bring the work back in line, and wait for my approval.
4. After approval, apply them, run the full checks (backend pytest + ruff; frontend typecheck + lint + tests) and report real results.
```

## Review prompt (after each phase)

```text
Review the changes from the last task as a strict reviewer. Check against AGENTS.md non-negotiable rules, PRD acceptance criteria for this phase, and ARCHITECTURE.md. Report: (1) violations, (2) missing tests, (3) security/privacy risks (private names, raw IPs, secrets, public endpoints that spend money), (4) accessibility and reduced-motion gaps, (5) anything claimed done but not verified. Do not change code; output a prioritized fix list.
```