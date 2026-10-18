# Hetu: Product Requirements Document (v2, "Living Platform")

Tagline: **Why it happened. What was said. What India felt.**

Status: v1 (search a case, wait for a job, read one dashboard) exists. This PRD defines v2. Read `ARCHITECTURE.md` for how to get from v1 to v2 and `RULES.md` for the non-negotiables.

---

## 1. Vision

Hetu is a public, always-on platform that puts three stories about Indian criminal cases side by side:

1. **The court's story**: what the judgment actually found (facts, motive, trigger, reasoning, outcome).
2. **The media's story**: how news framed it, and which claims match or contradict the judgment.
3. **The public's story**: what people think of the verdict, through polls and comments.

v1 behaves like a search-and-wait tool, which feels like a chatbot. v2 must feel like a **living newsroom-meets-courthouse**: open it and there is already something to read, track, vote on and explore. Nobody should need to type a prompt to get value.

## 2. Goals and non-goals

**Goals**
- Content-first: every page opens with real data, never an empty prompt box.
- Four anchor experiences: **Live Docket** (ongoing cases), **Verdicts** (decided cases), **Jan Mat** (public polls and comments), **Motive Atlas** (patterns across cases).
- A distinctive, dignified visual identity with purposeful animation (Lady Justice and the scales).
- TinyFish agents stay central: they keep the docket, judgments and media coverage fresh.
- Defensible ethics: transparent method, anonymization, moderation, no pre-judging of pending trials.

**Non-goals**
- Not a chatbot. No chat bubbles, no free-text "ask anything" box as the main UI.
- Not a predictor. No outcome, guilt or bail prediction. Ever.
- Not a forum for debating the guilt of people in pending trials.
- Not a legal-advice product.

## 3. Users

| Persona | Needs | Key surfaces |
|---|---|---|
| Criminology / law student | Patterns in motive and escalation, citable evidence | Motive Atlas, Verdicts |
| Journalist / fact-checker | Check media claims against judgments quickly | Verdicts (Media vs Court), Live Docket |
| Policy researcher / NGO | Perception gaps, public reaction themes | Jan Mat, Atlas, exports |
| Curious citizen | Understand a verdict in plain language, voice an opinion | Home, Jan Mat |
| Admin / curator (internal) | Add cases, review output, moderate | Admin |

## 4. Information architecture

Primary navigation (desktop top bar, mobile bottom bar or drawer):

1. **Home**
2. **Live Docket**: popular ongoing proceedings
3. **Verdicts**: decided cases with the full Media vs Court analysis
4. **Jan Mat**: public opinion, polls, comments
5. **Motive Atlas**: cross-case insights
6. **Methodology**: how scores work, limits, ethics, takedown/correction form
7. **Admin** (hidden, key-protected): add case, review, moderate

Header has a small **filter/search over existing content** only. It never starts analysis jobs.

## 5. Feature requirements

Priority: **P0** = must ship for the demo. **P1** = should. **P2** = stretch.

### 5.1 Home (P0)
- Hero with the **rotating scales of justice** animation (see section 6), tagline, and two buttons: "See the Live Docket" and "Vote on a verdict".
- **Three-story scroll section**: Court, Media, Public. Each is a card whose content animates in on scroll and links to the matching tab.
- **Featured cases** carousel (from the database, `featured = true`).
- **Poll of the week** card with live vote counts.
- **Docket ticker**: latest hearing updates, auto-scrolling, pausable.
- Live counters: cases analysed, votes cast, comments, judgments read (count up on first view).
- Acceptance: Largest Contentful Paint under 2.5 s on a mid-range laptop with the 3D/animation lazy-loaded; usable with animations disabled.

### 5.2 Live Docket (P0)
Purpose: follow popular ongoing proceedings, neutrally.
- **List**: card per case with anonymized title (or public-record title where the parties are public figures and the case is a matter of public record), court, category, **stage badge** (Investigation, Trial, Arguments, Judgment reserved, Appeal), **next hearing date**, last-updated stamp, and a 2 to 3 line neutral summary of the latest hearing.
- **Filters**: court, category, stage, "hearing this week". Sort: next hearing, most covered, recently updated.
- **Detail page**: hearing history timeline (draw-on-scroll), media coverage feed (outlet, date, headline, link, framing tag), "key questions before the court" (neutral bullets), and a **Follow** button (stored in local storage; no account needed).
- **No guilt polls and no verdict comments on ongoing cases.** The detail page shows a notice that polls open after judgment, and offers a subscription-free "notify me" bookmark only.
- Data comes from scheduled TinyFish refreshes ("last checked" must be visible).
- Acceptance: at least 8 ongoing cases seeded with at least 3 hearings each; every hearing entry links to a source.

### 5.3 Verdicts (P0)
- Library page of decided cases: filters by court, category, year, Perception Gap range.
- Case page is the existing dashboard (Gap Index, Timeline, Court vs Media, Media coverage, sources), restyled and made scroll-animated. Rename route `/cases` to `/verdicts` and keep a redirect.
- Add a **plain-language summary** at the top ("What the court decided, in simple terms", English; Hindi P1).
- Add a **"Vote on this verdict"** card linking to the matching Jan Mat poll.
- Every claim still has a **Source** link to the exact quote.
- Cases must be in `review_state = published` to be public.

### 5.4 Jan Mat: public opinion (P0)
Purpose: let people vote on and discuss decided judgments, and compare with the media and the court.
- **Index**: grid of open polls (decided cases only), sort by Trending, Newest, Most divided. "Poll of the week" pinned.
- **Intro animation** on first visit per session: Lady Justice **rotates, comes to face the viewer, and her blindfold lifts** (section 6.3). Skippable; reduced-motion users get a static "blindfold lifted" illustration.
- **Poll page**
  - Question: "Do you agree with the court's verdict?" Choices: **Agree**, **Partly agree**, **Disagree**.
  - Optional reason chips (multi-select): Sentence too lenient, Sentence too harsh, Justice was delayed, Evidence was handled well, Evidence was handled poorly, Procedure was fair, Media pressure affected it, Other.
  - Soft integrity step: show the plain-language summary above the vote and a "I have read the summary" checkbox (P1; do not hard-block).
  - **Results**: animated bars with percentages, total votes, and a "Not a representative sample" notice. Live updates via SSE (P1; polling every 10 s is acceptable for P0).
  - **Comments**: anonymous handles (auto-generated, e.g. "Citizen 4821", or a chosen nickname), one level of replies, upvote, report, sort by Top and Newest, 3 to 800 characters.
  - **Live Scales of Public Opinion (P1)**: dynamic SVG balance scale whose beam tilt angle and pan heights are driven by the live Agree vs Disagree vote share (Partly agree counts as half toward each side).
    - Animated with a spring curve (`spring({ bounce, duration })`) when vote results update via SSE or polling.
    - Zero votes: scales sit level with the label "No votes yet".
    - Small sample protection: below 10 votes, tilt angle is capped proportionally so a handful of votes cannot cause a dramatic swing.
    - Idle sway: subtle sine oscillation runs only when `prefers-reduced-motion` is off.
    - Optional drag-to-vote token: users can drag a token onto a pan to cast a vote. Hide the drag token when `(pointer: coarse)` matches (mobile/touch); accessible tap buttons are the primary control everywhere.
    - Must respect `prefers-reduced-motion`: instant balance settlement without spring oscillation.
  - **Public vs Media vs Court widget**: three gauges plus the Perception Gap Index, using first-party votes alongside scraped reactions (labelled separately).
- One vote per voter per poll (changeable). Rate limits apply (RULES.md).
- Moderation: see section 7.
- Acceptance: vote and comment flow works end to end with duplicate-vote protection; a held comment is invisible to others and visible in the admin queue.

### 5.5 Motive Atlas (P1, strongly recommended for the demo)
- Overview charts across all published cases: motive categories, trigger types, relationship between parties, escalation ladder (stages from dispute to violence), offence vs trigger Sankey, framing by outlet, Perception Gap distribution.
- Filters: court, year, category. Every chart point drills down to the underlying cases.
- Export CSV (aggregated and anonymized only).
- Empty or thin data states must say how many cases are in the sample.
- Acceptance: renders with at least 6 seeded cases; each chart shows `n`.

### 5.6 Methodology and ethics (P0, cheap and high value)
- How the Perception Gap Index is computed (reuse `scoring.py` explanations).
- Data sources and their robots.txt compliance.
- Limits: online opinion is not representative; LLM extraction can err; reviewed before publishing.
- Takedown and correction form (writes to `reports`/`corrections` table, emails nobody; admin sees it).
- Sub judice policy: no polls on pending trials.

### 5.7 Admin (P0 minimal)
- `POST /admin/cases` replaces the public case-creation endpoint. Add a case by name, court, category and status (ongoing or decided). It enqueues a background job.
- Review queue: preview extraction, edit or remove a claim, approve to publish.
- Moderation queue: held and reported comments, approve or remove.
- Ingestion monitor: job list with status, provider, duration, cost estimate.
- Protected by `ADMIN_API_KEY` for MVP.

## 6. Visual and animation requirements

### 6.1 Design language
Keep the dark editorial theme: near-black background, ivory text, burnt-gold accents, Playfair Display headings, Manrope body. Add Noto Sans/Serif Devanagari for Hindi labels. Tone: serious, respectful. No confetti, no jokes, no emojis in the UI.

### 6.2 Home: rotating scales
- Slowly rotating scales of justice at the hero center (Y-axis rotation about 8 s per turn), pans gently swaying, subtle mouse parallax.
- On scroll, the scales tilt toward whichever story card (Court, Media, Public) is in view via Anime.js `onScroll` synchronization.
- Implementation order: **P0 layered SVG/CSS 3D** with Anime.js v4 (deterministic); **P1 React Three Fiber** with a licensed GLB (see ARCHITECTURE.md section 8).

### 6.3 Jan Mat: Lady Justice reveal (the signature moment)
Anime.js timeline (`createTimeline()`, about 3.5 s, once per session, skippable):
1. 0.0 to 0.4 s: statue visible from behind, fade in.
2. 0.4 to 2.4 s: rotates 360 degrees with ease-in-out (`inOutQuad`) and a slight scale pulse.
3. 2.0 to 2.8 s (as she comes back to face the viewer): **blindfold unties** (band lifts, slides off with a small rotation and fades) and eyes are revealed.
4. 2.8 to 3.5 s: scales settle, page content staggers in (`stagger(100)`). Caption: "Justice is blind. The public is not."
- Honour `prefers-reduced-motion`: show the final frame statically via `createScope` media query.
- Pause when the tab is hidden. Never block interaction beyond the skip button. Clean up via `scope.revert()`.

### 6.4 Global motion
- Animation engine: **Anime.js v4** for timelines, SVG line drawing (`createDrawable`), spring physics (`spring`), draggable tokens (`createDraggable`), count-up numbers, gauge needles, and scroll synchronization (`onScroll`).
- Page transitions: **Framer Motion** strictly for page/component enter/exit (`AnimatePresence`).
- Scrolling: native browser scrolling with modern CSS `position: sticky` for pinned story sections; Lenis is removed.
- Skeleton loaders everywhere data loads. No spinners longer than 1 s without skeletons.
- Budget: animation work must not drop interaction below 60 fps on a mid-range laptop; 3D must be lazy-loaded and disabled on low-end devices.

## 7. Moderation and safety requirements (P0)

Comments pipeline (all server-side):
1. Validate length and rate limit (5 comments per hour per voter).
2. Strip contact details (reuse the anonymizer regexes).
3. Mask names of private individuals registered for that case.
4. Profanity and abuse check (English plus Hindi/Hinglish list). Hits go to **held**.
5. Contempt guard: threats or calls for violence, and personal attacks on judges (as opposed to criticism of reasoning), go to **held**.
6. Three reports auto-hide a comment pending review.
7. (P1) Async LLM label for stance and theme; never used to remove comments automatically.

Polls open only after a judgment is delivered. Disclaimer on all Jan Mat pages: opinions are not legal advice and not a representative sample; criticize reasoning, not people.

## 8. Data requirements (summary; full schema in ARCHITECTURE.md)
New entities: `hearings`, `polls`, `votes`, `comments`, `comment_votes`, `reports`, `corrections`, plus new columns on `cases` (`status`, `review_state`, `featured`, `decided_on`, `next_hearing_on`).

## 9. Non-functional requirements
- **Speed**: all public pages read precomputed data; no public request triggers an LLM or TinyFish call.
- **Ingestion time** (40 to 50 minutes per case today) is acceptable only because it is **offline and invisible**. Target after fixes: under 15 minutes per case on a paid provider.
- **Accessibility**: WCAG AA contrast, keyboard navigation, chart alt text and data tables, reduced-motion support.
- **Responsive**: mobile-first; the Lady Justice reveal and scales must degrade gracefully.
- **Language**: English at launch; Hindi labels P1.
- **Privacy**: no accounts required; store voter hashes, never raw IPs; no private names in logs.
- **Reliability**: one database (Postgres) for local and Docker; jobs survive restarts (queue).

## 10. Seed content (verify everything before publishing)
- Decided: the Jessica Lal case (already collected) and at least 5 other well-documented Delhi or national cases chosen by the team. Avoid sexual-offence cases and cases with minors.
- Ongoing: 8 or more popular proceedings found through TinyFish news and court-site agents. The team confirms each is a matter of public record before publishing.
- All seed cases pass human review (`review_state = published`).

## 11. Phasing (maps to PROMPTS.md)
1. Audit and plan (no code)
2. Data model and migrations
3. Poll, vote and comment APIs plus moderation
4. Docket ingestion (TinyFish) and scheduler
5. Design system and app shell
6. Home and scales animation
7. Live Docket UI
8. Jan Mat UI and Lady Justice reveal
9. Verdicts refactor
10. Atlas APIs and page
11. Admin and review
12. Pipeline speed and seeding
13. Tests, accessibility and polish
14. Docker and deploy

## 12. Success criteria for the demo
- A judge opens the site and within 10 seconds sees motion, real cases and a poll.
- Live Docket shows at least 8 cases with fresh "last checked" times.
- A live vote and a comment show up on screen, and the Public vs Media vs Court widget updates.
- Motive Atlas shows patterns with sample sizes.
- Methodology page answers the ethics questions before they are asked.

## 13. Risks and mitigations
| Risk | Mitigation |
|---|---|
| Sub judice / contempt concerns | No polls on pending cases; neutral docket text; moderation; methodology page |
| LLM extraction errors | Verbatim quote checks, human review gate, visible sources |
| Court portals block or change | Cached bundles, open-dataset fallback, graceful "last checked" states |
| Poll manipulation | Signed anonymous voter id, one vote per poll, rate limits, "not representative" labelling |
| Animation hurting performance | Lazy-load, reduced-motion, 3D feature flag |
| Hackathon rules on pre-built work | Confirm with organizers what is allowed before the finale (see team notes) |