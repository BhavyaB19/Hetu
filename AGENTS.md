# Hetu: Agent Rules

Use as repo-root `AGENTS.md` (or `GEMINI.md`), and/or copy into `.agents/rules/hetu.md` (older Antigravity builds use `.agent/rules/`). Keep this file under 12,000 characters. Do not add a second file that contradicts it.

## Project in one paragraph
Hetu puts three stories about an Indian criminal case side by side: the court's (judgment), the media's (news), the public's (polls and comments), and scores the difference (Perception Gap Index). Stack: FastAPI + async SQLAlchemy + Alembic + Postgres + Redis/arq (backend), Next.js 15 + React 19 + Tailwind 4 + TypeScript (frontend), TinyFish agents for web collection. Read `PRD.md` (what) and `ARCHITECTURE.md` (how) before any task.

## Non-negotiable product rules
1. **Not a chatbot.** No chat bubbles, no "ask anything" input as the main UI. Pages open with real content.
2. **No prediction.** Never add outcome, guilt, bail or sentence prediction.
3. **Polls and comments only on decided, published cases.** Ongoing cases get tracking only. Enforce in the database layer and in the API, not just the UI.
4. **Anonymize before storing**, including comments. Private individuals (accused, victims, witnesses, relatives, minors) become placeholders. Judges, lawyers and officials acting officially are not anonymized. Never log private names.
5. **Evidence for every claim.** Findings, claims and timeline events keep a verbatim quote span that is validated against the source. Drop unverifiable claims instead of guessing.
6. **Public content only.** Respect robots.txt. No logins, no account creation, no CAPTCHA solving, no paywall bypass. Do not use sites already found to block agents.
7. **Public requests never trigger LLM or TinyFish calls or spend money.** Ingestion runs only as admin-started or scheduled background jobs.
8. **Copyright-aware storage.** Store excerpts and links in the database, not full article text. Full text only in the git-ignored local cache.
9. **Tone**: dignified. No jokes, emojis or celebratory effects in the UI. Criticize reasoning, not people.

## Workflow rules
- **Plan first.** For any task longer than a small fix, write a short plan (files to touch, steps, risks) and wait for approval when running in review mode. Do not start coding from an unclear spec; list assumptions and questions instead.
- **Small, reviewable changes.** One concern per change set. Do not refactor unrelated code.
- **Run before claiming done.** Backend: `cd backend && pytest && ruff check .`. Frontend: `cd frontend && npm run typecheck && npm run lint && npm test`. Report results honestly. If something fails, say so and fix it or explain.
- **Never invent APIs.** Check the existing code, `PRD.md`, `ARCHITECTURE.md` and the generated OpenAPI before using an endpoint or field. If the TinyFish API behaviour is unclear, read its docs rather than guessing parameters.
- **Dependencies.** Use only the approved list in `ARCHITECTURE.md` section 10. If you need something else, stop and propose it with a reason.
- **Secrets.** Never commit `.env`, API keys or `fixtures/collected/`. Use `.env.example` for documentation. Never print keys in logs.
- **Generated files.** Never hand-edit `frontend/src/lib/api/schema.d.ts`. After changing `schemas/views.py`, run `python backend/scripts/export_openapi.py` then `npm --prefix frontend run gen:api`.
- **Migrations.** Every schema change gets an Alembic migration and passes `alembic check`. Write reversible migrations. Do not edit applied migrations.
- **Do not touch** without being asked: `backend/fixtures/jan-mat-v-state.json` (demo/test data), existing test expectations (fix code, not tests, unless the test is wrong and you explain why), license or disclaimer text.
- **Ask before** deleting files, renaming public routes (add redirects instead), or changing scoring weights.

## Backend rules
- Python 3.11+, full type hints, Pydantic v2 models for all request and response bodies, `async` end to end.
- Routers stay thin; logic lives in `services/`; database access only through `db/repository.py` (or new repositories alongside it).
- All timestamps are timezone-aware UTC.
- Use `structlog`/standard logging with user-readable messages; no private names, no raw IPs, no comment bodies in logs.
- Validation: reject early with clear 4xx messages. Never return stack traces.
- Rate limit vote, comment, report and admin routes with `slowapi` (Redis storage).
- Votes: unique (`poll_id`, `voter_hash`); changing a vote updates the row. Voter identity = signed cookie id, hashed with `VOTER_HASH_SECRET`. Do not store raw IPs.
- Comments pipeline order: validate, strip contact details, mask registered private names, abuse check, contempt check, then set status `visible` or `held` with a reason. Never auto-remove; hold for review.
- LLM calls: structured output, verbatim-quote validation, retries with the problem list, timeouts, and the daily budget guard. Provider is configured only by env; no silent fallback to another provider.
- Jobs: use arq. Jobs must be idempotent and safe to retry.
- Tests: pytest with fakes for TinyFish and every LLM; no network or keys needed. Add tests for every new service and every moderation branch.

## Frontend rules
- TypeScript strict. No `any`. Use generated API types from `lib/api/schema.d.ts`.
- Server components by default; client components only for interactivity and animation. All API calls go through server-side proxies in `app/api/` or server components; the browser never sees `ADMIN_API_KEY`.
- UI: shadcn/ui + Tailwind with design tokens from `globals.css` (`--color-*`). No hard-coded hex values or arbitrary pixel sizes in components when a token exists.
- Typography: Playfair Display (headings), Manrope (body), Noto Sans/Serif Devanagari for Hindi.
- Data fetching: TanStack Query on the client with sensible `staleTime`; skeleton loaders for every async region; empty, error and loading states for every screen.
- Forms: react-hook-form + zod. Show clear validation messages. Never block on animation.
- **Animation rules**
  - Library roles: Anime.js v4 (`animejs`) for timelines, SVG line drawing, scroll choreography (`onScroll`), spring physics (`spring`/`createSpring`), draggable tokens (`createDraggable`), and data-bound gauges; Framer Motion strictly for page transitions and component enter/exit; no GSAP/ScrollTrigger; no Lenis (use native scroll + `position: sticky`); React Three Fiber only behind `NEXT_PUBLIC_ENABLE_3D`.
  - Always encapsulate Anime.js instances in `createScope({ root })` inside client components (`"use client"`), and call `scope.revert()` in `useEffect` cleanup to guarantee zero memory leaks and clean React 19 StrictMode double-mounting.
  - Always honour `prefers-reduced-motion` using `createScope` `mediaQueries: { reduceMotion: '(prefers-reduced-motion: reduce)' }` (render the final state, no looping motion). Idle sway runs only when reduced motion is off.
  - Heavy animation is lazy-loaded (`next/dynamic`, `ssr: false`); pause when the tab is hidden (`document.hidden`).
  - Animate `transform` and `opacity` only; never animate layout properties in loops.
  - Lady Justice reveal: driven by scroll (frames from video, never a timer), reversible, with an always-visible skip link; reduced motion shows the end state; never hides required content.
- Accessibility: WCAG AA contrast, visible focus states, keyboard operable controls, `aria-label`s on icon buttons, charts with accessible data tables, `aria-live` for vote results, semantic landmarks. Run axe checks in Playwright.
- Responsive: mobile first; test at 375 px, 768 px and 1280 px widths.
- Performance: no layout shift from images or fonts (set sizes, use `next/font`), keep the Home JS payload small, defer 3D.
- Copy: plain English, short sentences. Always show "Not a representative sample" near poll results and "Illustrative demo" on demo data.

## Design system summary
Newsprint and court: greyish newsprint ground, printer's-ink text, oxblood seal-red accent used sparingly, muted ink greys for secondary text. Ink blocks (`.reverse`) for the Jan Mat band and the footer. The jaali (carved sandstone lattice, `components/jaali/`) is the structural motif: arches frame content, the Home hero opens a carved screen. Token names predate the palette, so read them by role: `--color-ink` is the ground, `--color-ivory` the text, `--color-gold` the accent. Four chart inks (`--color-viz-1..4`) chosen for colour-blind separation; never encode meaning by colour alone (add labels or patterns). Serif headings, hairline rules, generous spacing. Buttons: seal-red primary (`.btn-seal`), bordered secondary (`.btn-plain`). Stage and verdict badges use text plus icon, not colour only.

## Definition of done
A task is done only when: code compiles; tests and lint pass; new behaviour has tests; migrations apply and roll back; types are regenerated; accessibility and reduced-motion are handled; no private names or secrets in logs or commits; `README.md` or `ARCHITECTURE.md` is updated if behaviour or setup changed; and the change set is summarized (what changed, why, how to verify, known gaps).

## Never do
Add a chat UI. Predict outcomes. Open polls on pending cases. Scrape behind logins or bypass CAPTCHAs. Spend money from a public request. Store raw IPs or private names. Edit generated files by hand. Commit collected fixtures or `.env`. Silence a failing test by deleting it. Claim something works without running it.