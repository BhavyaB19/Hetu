# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary users depend on the surface:

- **Home and Jan Mat** favour the **curious citizen**, who wants a verdict in plain language and a dignified way to give an opinion on it.
- **Verdicts, Live Docket and Motive Atlas** favour professionals: **journalists and fact-checkers** checking media claims against judgments, **law and criminology students** studying motive and escalation patterns with citable evidence, and **policy researchers and NGOs** looking at perception gaps and public reaction themes.
- **Admin / curator** (internal, key-protected) adds cases, reviews extractions before they are published, and moderates comments.

## Product Purpose

Hetu puts three stories about an Indian criminal case side by side: the court's (the judgment), the media's (news coverage) and the public's (polls and comments). It scores how far the media and public drift from the court with the Perception Gap Index (0 means aligned, 100 means far apart). Tagline: **"Why it happened. What was said. What India felt."** "Hetu" means cause or reason.

Near-term success is the **hackathon finale demo**. Within 10 seconds of opening the site, a judge should see motion, real cases and a poll. The Live Docket should show at least 8 cases with fresh "last checked" times. A live vote and a comment should appear on screen. The Motive Atlas should show patterns with sample sizes. The Methodology page should answer ethics questions before anyone asks them (PRD.md §12).

## Positioning

Hetu is the one place where the court's story, the media's story and the public's story about the same Indian criminal case sit side by side. Linking every claim to its evidence and scoring the gap make that comparison credible, but the core claim is that the three stories appear together.

## Operating Context

- It is a living, always-on platform, not search-and-wait. Every page opens with real content. There is no prompt box.
- Four anchor surfaces: **Live Docket** (ongoing cases, tracking only), **Verdicts** (decided cases with the full Media vs Court analysis), **Jan Mat** (polls and comments on decided cases), **Motive Atlas** (patterns across cases). Supporting surfaces: **Methodology** (scoring, limits, ethics, takedown and correction form) and **Admin**.
- Content is gathered offline by TinyFish browser agents and LLM extraction, goes through human review, and is published with `review_state = published`. Public requests only read precomputed data.
- Demo data: *Jan Mat v. State* is an illustrative case, not a real one, and must be labelled "Illustrative demo".

## Capabilities and Constraints

- **Not a chatbot.** No chat bubbles. No "ask anything" input as the main UI.
- **No prediction.** No outcome, guilt, bail or sentence prediction, ever.
- **Polls and comments only on decided, published cases.** Ongoing cases get neutral tracking and a "polls open after judgment" notice.
- **Anonymized.** Private individuals (accused, victims, witnesses, relatives, minors) appear as placeholders such as `[VICTIM_1]`. Judges, lawyers and officials acting officially are named.
- **Evidence for every claim.** Every finding, claim and timeline event links to a verbatim source quote (the § Source link).
- **No accounts.** Voters get anonymous handles (for example "Citizen 4821"). Follow and bookmark state lives in local storage.
- Poll choices: Agree, Partly agree, Disagree, with optional reason chips. Results always carry "Not a representative sample".
- Language: English at launch, Hindi labels P1.
- Stack: Next.js 15, React 19, Tailwind 4, TypeScript. Anime.js v4 for timelines, scroll and springs. Framer Motion only for page and component enter/exit. No GSAP and no Lenis. 3D only behind `NEXT_PUBLIC_ENABLE_3D`. See AGENTS.md and architecture.md §10 for approved dependencies.
- Performance: LCP under 2.5 s on a mid-range laptop. The site must be usable with animation disabled.

## Brand Commitments

- **Name and voice:** Hetu. Dignified, serious and respectful. Plain English in short sentences. Criticize reasoning, not people. No jokes, emojis, confetti or celebratory effects.
- **Binding visual constraints** (AGENTS.md): newsprint and court. A greyish newsprint ground, printer's-ink text, an oxblood seal-red accent used sparingly, ink blocks for reversed panels, and a carved sandstone jaali as the structural motif. Playfair Display for headings, Manrope for body text, Noto Serif Devanagari for Hindi. Four colour-blind-separated chart inks (`--color-viz-1..4`). Meaning is never carried by colour alone.
- **Signature motifs:** the jaali (carved stone screen) and Lady Justice behind it on the Home page. Scrolling opens the screen, she turns, the blindfold falls, and the caption reads "Justice is blind. The public is not." The reveal is scroll-driven and reversible, and shows its end state under reduced motion. The scales of justice remain on Jan Mat (live opinion scales driven by vote share) and on each verdict (coverage weighed against the judgment).

## Evidence on Hand

- Illustrative demo case: `backend/fixtures/jan-mat-v-state.json`, with a High Court judgment, five fictional outlets and 16 reactions.
- Real collected cases (Jessica Lal, Mihir Rajesh Shah v. State of Maharashtra) sit in `backend/fixtures/collected/`. They contain pre-anonymization names and full text, so they are not for public display until reviewed.
- Art: `frontend/public/art/` (`lady-back.svg`, `lady-front.svg`, `scales-hero.svg`) and the Lady Justice video frames in `frontend/public/media/lady/`.
- No testimonials, press, user counts or partnerships exist. Do not fabricate any. Live counters must reflect real database values.

## Product Principles

1. **Content first.** Every page opens with something real to read, track or vote on.
2. **The record leads.** The court's story is the reference point. Media and public stories are measured against it, never the other way round.
3. **Show the evidence.** If a claim can't be traced to a quote, it doesn't appear.
4. **Never pre-judge.** Pending cases get neutral tracking only. No opinion surfaces and no prediction.
5. **Dignity over spectacle.** Motion and drama serve understanding of a serious subject, and never make light of crimes or the people in them.

## Accessibility & Inclusion

WCAG AA contrast, visible focus states, keyboard-operable controls, `aria-label`s on icon buttons, charts with accessible data tables, `aria-live` for vote results, and semantic landmarks. Full `prefers-reduced-motion` support: every animation has a static end state. Mobile first, tested at 375, 768 and 1280 px. Hindi readers will be served through Devanagari labels (P1).
