# Anime.js v4 Migration & Feasibility Report for Hetu

**Platform**: Hetu ("Why it happened. What was said. What India felt.")  
**Author**: Antigravity AI  
**Scope**: Phase A Audit & Feasibility Assessment (Anime.js v4 core animation engine + Live Scales of Public Opinion)  
**Status**: Complete — Awaiting User Approval to proceed to Phase B  

---

## 1. Current State: What Exists Today vs What the Four Docs Require

The four root specification documents (`prd.md`, `architecture.md`, `prompts.md`, `rules.md`) define Hetu v2 as a living editorial platform with 4 anchor experiences: Live Docket, Verdicts, Jan Mat, and Motive Atlas. The codebase currently sits in **v1 state**, which acts as a search-and-wait tool.

| Area / Feature | Documented Requirement (v2) | Current Codebase State (v1) | Gap Analysis |
|---|---|---|---|
| **Animation Engine** | Framer Motion (page transitions), GSAP + ScrollTrigger (timelines, scroll, scales), Lenis (Home/Jan Mat), R3F (P1 3D) | No animation or UI libraries installed (`frontend/package.json` contains only Next.js 15.5.28, React 19.1.0, Tailwind CSS 4, openapi-fetch) | Zero legacy GSAP or Framer code exists in the repo. Clean slate for Anime.js v4. |
| **Home Landing** | Rotating scales hero (SVG/CSS 3D), three-story scroll section (Court, Media, Public), featured cases carousel, live counters, docket ticker | Search box (`CaseSearch.tsx`) querying/starting jobs, static 3-story cards, simple cases list | Public job-search UI must be replaced by animated hero and docket ticker. |
| **Live Docket** | Ongoing cases tracking (`/docket`, `/docket/[slug]`), stage badges, hearing history timeline with draw-on-scroll line, neutral summaries, sub judice policy | None. No `/docket` routes, no `hearings` table, no `DocketAgent`. | Full implementation required per Prompts 4 & 7. |
| **Verdicts Library** | Decided cases at `/verdicts` and `/verdicts/[slug]`, plain-language summaries, vote card, animated gap score & evidence links | Located at `/cases` and `/cases/[slug]`. Dashboard exists (`CourtVsMedia`, `GapIndex`, `Timeline`, `EvidenceLink`), but lacks scroll reveals and redirect from `/cases`. | Needs route rename to `/verdicts`, redirect in `next.config.ts`, plain summary, and scroll reveals. |
| **Jan Mat (Public Opinion)** | Open polls on decided cases (`/jan-mat`), Lady Justice reveal animation, Agree/Partly/Disagree votes, reason chips, live results bars (SSE), comments with moderation, Public vs Media vs Court widget | Only thin scraped comments stored in `public_reactions` table (`PublicReaction.tsx`). No first-party polls, votes, or comment system. | Full implementation required per Prompts 3 & 8. |
| **Live Scales of Public Opinion (New)** | Real-time dynamic SVG balance scale whose beam tilt angle and pan heights are driven by Agree vs Disagree vote ratio; spring physics; optional drag-to-vote token | Not in v1 or original v2 docs. | Proposed new P1 feature for Jan Mat. |
| **Motive Atlas** | Cross-case analysis (`/atlas`) with motive bars, escalation ladder, Sankey chart, outlet framing, CSV export | None. No `/atlas` route or `/insights/*` endpoints. | Full implementation required per Prompt 10. |
| **Database & Queue** | Single PostgreSQL database everywhere, Redis + arq queue, daily cron for docket refreshes | SQLite locally via `aiosqlite`, in-memory background tasks (`services/jobs.py`), Postgres in Docker only | Local SQLite default must be removed in favor of Docker/local PostgreSQL. |
| **Case Administration** | Admin-only case creation (`POST /admin/cases`), review queue, claim editor, comment moderation queue | Public `POST /cases` starts LLM jobs directly; public user can trigger paid API consumption | Remove public job endpoint; build admin API with `ADMIN_API_KEY`. |
| **Design System** | Dark editorial theme, CSS variables in `globals.css` (`--color-ink`, `--color-gold`, `--color-viz-1..4`), Playfair Display, Manrope, Devanagari font | `globals.css` has basic palette and Tailwind 4 `@theme`, but no shadcn/ui components or Devanagari font setup. | UI components and typography need completion. |

---

## 2. Required Document Changes

To adopt Anime.js v4 and integrate the "Live Scales of Public Opinion" feature, the four root documents must be updated in Phase B as follows:

### 2.1 `rules.md` (and `AGENTS.md`)
*Constraint: Must remain under 12,000 characters (currently 8,516 characters).*

- **Section: Frontend rules > Animation rules (lines 51–56)**:
  - **Current Text**:
    ```markdown
    - Animation rules
      - Library roles: Framer Motion for component enter/exit and page transitions; GSAP + ScrollTrigger for timelines and scroll choreography; Lenis only on Home and Jan Mat; React Three Fiber only behind NEXT_PUBLIC_ENABLE_3D.
      - Always honour prefers-reduced-motion (render the final state, no looping motion).
      - Heavy animation is lazy-loaded (next/dynamic, ssr: false); kill ScrollTriggers/timelines in cleanup; pause when the tab is hidden.
      - Animate transform and opacity only; never animate layout properties in loops.
      - Lady Justice reveal: runs once per session (sessionStorage), skippable, max 3.5 s, never hides required content.
    ```
  - **Proposed Replacement**:
    ```markdown
    - Animation rules
      - Library roles: Anime.js v4 for timelines, SVG line drawing, scroll choreography, spring physics, draggable tokens, and data-bound gauges; Framer Motion strictly for page transitions and component enter/exit; Lenis only if smooth scroll is retained; React Three Fiber only behind NEXT_PUBLIC_ENABLE_3D.
      - Always wrap Anime.js instances in `createScope({ root })` inside client components (`"use client"`), and call `scope.revert()` in `useEffect` cleanup to guarantee zero memory leaks and clean React 19 StrictMode double-mounting.
      - Always honour `prefers-reduced-motion` using `createScope` `mediaQueries: { reduceMotion: '(prefers-reduced-motion: reduce)' }` (render the final state, no looping motion).
      - Heavy animation is lazy-loaded (`next/dynamic`, `ssr: false`); pause when the tab is hidden (`document.hidden`).
      - Animate `transform` and `opacity` only; never animate layout geometry (width, height, top, left) in continuous loops.
      - Lady Justice reveal: runs once per session (`sessionStorage`), skippable, max 3.5 s, never hides required content.
    ```

### 2.2 `prd.md`
- **Section 5.4: Jan Mat: public opinion (insert new requirement under Poll page, around line 98)**:
  - **Proposed Addition**:
    ```markdown
    - Live Scales of Public Opinion (P1): an interactive SVG balance scale whose beam tilt angle and pan vertical heights are driven by the live Agree vs Disagree vote ratio (Partly agree counts as 50% toward each side). Animates with physics-based spring curves upon vote submission or SSE result stream updates. Includes an optional drag-to-vote token that users can drag onto a pan, alongside standard accessible radio/button fallbacks. Must respect prefers-reduced-motion (instant balance settlement without spring oscillations).
    ```
- **Section 6.2: Home: rotating scales (lines 129–133)**:
  - Update implementation order to specify Anime.js v4 + CSS 3D for the P0 layered SVG implementation instead of GSAP.
- **Section 6.3: Jan Mat: Lady Justice reveal (lines 134–142)**:
  - Specify Anime.js v4 `createTimeline()` for the 3.5s sequence (fade in, 360-degree Y rotation, `#blindfold` translation/rotation/fade-out, content stagger).
- **Section 6.4: Global motion (lines 143–149)**:
  - **Proposed Text**:
    ```markdown
    - Page transitions (fade and slight rise) via Framer Motion.
    - SVG line-draw, staggered reveals, count-up numbers, animated gauges and needles, spring-driven vote scales, and scroll choreography via Anime.js v4.
    - Clean up all animations via `scope.revert()`.
    ```

### 2.3 `architecture.md`
- **Section 3: Change Table (Row 13, line 62)**:
  - Change "Design system plus scroll/page animation plus Lady Justice" to reflect Anime.js v4 + Framer Motion.
- **Section 8: Frontend structure > Animation implementation (lines 165–177)**:
  - **Current Text**: Mentions GSAP timelines, GSAP ScrollTrigger for scales tilt and timeline drawing, and `useGSAP` cleanup.
  - **Proposed Replacement**:
    ```markdown
    ### Animation implementation (Anime.js v4)

    **Scales hero (P0): layered SVG + CSS 3D.** Build `ScalesHero` from an SVG with groups `#base`, `#beam`, `#pan-left`, `#pan-right`. Beam sways with a gentle sine oscillation via Anime.js (`animate(beam, { rotate: [-3, 3], loop: true, alternate: true, ease: 'inOutSine', duration: 3000 })`). Y-axis spin uses CSS `perspective` and `rotateY` on a wrapper; front and back art layers maintain `backface-visibility: hidden`.

    **Lady Justice reveal (P0): Anime.js timeline.**
    - Assets: `public/art/lady-front.svg` (with `<g id="blindfold">`), `public/art/lady-back.svg`.
    - Anime.js timeline (`createTimeline`): `rotateY: [0, 360]` (2000 ms, `inOutQuad`); at 1600 ms animate `#blindfold` (`translateX: 40, rotate: 25, opacity: 0, duration: 600`) and fade in eyes; then stagger page content with `stagger(100)`.
    - Persist `sessionStorage.hetuReveal = "1"`; skip button; `prefers-reduced-motion` renders the end state immediately.
    - Encapsulated in `createScope({ root })` with cleanup via `scope.revert()`.

    **Live Scales of Public Opinion (P1): Spring-driven data visualization.**
    - SVG balance scale where Agree votes lower the left pan and tilt the beam counter-clockwise; Disagree votes lower the right pan; Partly Agree splits evenly.
    - Tilt angle `theta = clamp((agree - disagree) / total * MAX_TILT, -MAX_TILT, MAX_TILT)`.
    - When new votes arrive (SSE or poll response), animate rotation and pan `translateY` using `spring({ bounce: 0.35, duration: 800 })`.
    - Optional vote token uses `createDraggable(tokenRef, { container, onRelease })` with accessible button fallback.

    **Scroll motion**: Anime.js `onScroll({ sync: true, target, enter, leave })` for scrubbed timelines and SVG stroke drawing via `svg.createDrawable()`. For pinned scenes on Home (Court, Media, Public), utilize standard CSS `position: sticky` with top offset tracks rather than DOM-wrapping JS pins.
    ```
- **Section 10: Dependencies (Approved list, line 191–199)**:
  - **Remove**: `gsap`, `@gsap/react`.
  - **Add**: `animejs` (`^4.0.0`).
  - **Retain**: `framer-motion` (for React page/component enter/exit), `lenis` (optional smooth scrolling on marketing surfaces), `three`, `@react-three/fiber`, `@react-three/drei` (P1 3D behind `NEXT_PUBLIC_ENABLE_3D`).

### 2.4 `prompts.md`
- **Prompt 6: Home page and scales animation (lines 117–132)**:
  - Replace GSAP ScrollTrigger mentions with Anime.js v4 `onScroll` and `createScope`. Specify CSS `position: sticky` for the three-story scroll section.
- **Prompt 8: Jan Mat UI and Lady Justice reveal (lines 148–163)**:
  - Replace GSAP timeline with Anime.js `createTimeline()`.
  - Add explicit task: Build `LiveScales.tsx` in `components/jan-mat/` using Anime.js `spring()` for vote-share tilt and `createDraggable()` for the optional voting token.
- **Optional Prompt A: React Three Fiber upgrade (lines 258–268)**:
  - Replace GSAP timeline for blindfold with Anime.js / R3F `useFrame` or `animejs/dist/modules/adapters/three`.

---

## 3. Required Code Changes

### 3.1 Dependencies (`frontend/package.json`)
- Add: `animejs`: `^4.0.0`
- Add: `framer-motion`: `^12.0.0` (for page/dialog enter/exit)
- Add: `lucide-react`, `clsx`, `tailwind-merge`, `class-variance-authority`, `sonner`
- Note: Neither GSAP nor `@gsap/react` is currently installed; no package removal is needed.

### 3.2 Files to Add
```
frontend/src/
  components/
    motion/
      ScalesHero.tsx          # Anime.js + CSS 3D rotating hero scales with mouse parallax
      LadyJusticeReveal.tsx   # Anime.js createTimeline 3.5s reveal with blindfold lift
      DrawLine.tsx            # Anime.js svg.createDrawable + onScroll line drawer
      CountUp.tsx             # Anime.js animated numerical counter
      PageTransition.tsx      # Framer Motion AnimatePresence route wrapper
    jan-mat/
      LiveScales.tsx          # Spring-driven Agree vs Disagree balance scale + draggable token
      VoteWidget.tsx          # Accessible vote controls (Agree/Partly/Disagree + reason chips)
      ResultsBars.tsx         # Animated vote share percentage bars
      CommentThread.tsx       # Anonymous moderated comments
    docket/
      HearingTimeline.tsx     # Hearing history with Anime.js scroll-drawn connecting line
  lib/
    motion/
      anime.ts                # Helper utilities for Anime.js createScope in React 19
```

### 3.3 Files to Modify
- `frontend/src/app/page.tsx`: Replace `CaseSearch` with `ScalesHero`, add three-story sticky storytelling section, featured cases carousel, docket ticker.
- `frontend/src/app/globals.css`: Add styles for sticky scroll containers, 3D perspective, and CSS variables for SVG balance arm pivots.
- `frontend/src/app/layout.tsx`: Wrap page children in `PageTransition` (Framer Motion).
- `frontend/src/app/cases/`: Rename folder to `frontend/src/app/verdicts/` and add redirect in `next.config.ts`.
- `backend/app/core/config.py`: Remove SQLite fallback; make PostgreSQL `DATABASE_URL` standard.

### 3.4 Conflicting Implementations
- **No GSAP conflicts**: No GSAP code or dependencies exist in the repository.
- **Route naming conflict**: `frontend/src/app/cases` exists; must be moved to `/verdicts` with a temporary 308 redirect for backward compatibility.
- **Search-as-hero conflict**: `CaseSearch.tsx` is currently embedded as the main hero element in `app/page.tsx`; must be removed from the hero and placed in the global nav header as a query-only filter.

---

## 4. Feasibility Verdicts for Proposed Features & Architecture

Each item below has been audited against the Anime.js v4 official documentation ([animejs.com/documentation](https://animejs.com/documentation)) and the existing React 19 / Next.js 15 codebase.

---

### a. Lady Justice reveal (spin, blindfold lift, content stagger) with `createTimeline`
- **Verdict**: **FULLY POSSIBLE**
- **Effort**: **M**
- **Documentation Citation**: [Timeline Docs](https://animejs.com/documentation/timeline), [Timeline Methods](https://animejs.com/documentation/timeline/timeline-methods), [Using with React](https://animejs.com/documentation/getting-started/using-with-react)
- **Technical Mechanism**:
  `createTimeline({ defaults: { ease: 'inOutQuad' } })` orchestrates:
  1. `tl.add('.lady-wrapper', { opacity: [0, 1], duration: 400 }, 0)`
  2. `tl.add('.lady-figure', { rotateY: [0, 360], duration: 2000, ease: 'inOutCubic' }, 400)`
  3. `tl.add('#blindfold', { translateX: 40, rotate: 25, opacity: 0, duration: 600, ease: 'outQuad' }, 2000)`
  4. `tl.add('.lady-eyes', { opacity: [0, 1], duration: 400 }, 2200)`
  5. `tl.add('.stagger-content', { opacity: [0, 1], translateY: [20, 0], delay: stagger(100), duration: 700 }, 2800)`
  Wrapped in `createScope({ root })`. Stored in `sessionStorage.hetuReveal = "1"`. Skippable via button that invokes `tl.complete()`.

---

### b. Scales hero (beam sway, pan sway, CSS 3D rotateY, parallax)
- **Verdict**: **FULLY POSSIBLE**
- **Effort**: **M**
- **Documentation Citation**: [Animation Docs](https://animejs.com/documentation/animation), [CSS Transforms](https://animejs.com/documentation/animation/animatable-properties/css-transforms)
- **Technical Mechanism**:
  - Continuous subtle beam sway: `animate('#beam', { rotate: [-3, 3], duration: 3200, loop: true, alternate: true, ease: 'inOutSine' })`.
  - Pan counter-rotation: left pan `#pan-left` rotates `[3, -3]` and right pan `#pan-right` rotates `[3, -3]` with matching duration to stay vertically upright.
  - 3D container: CSS `perspective: 1200px` on parent; wrapper rotates via CSS keyframes or Anime.js `animate('.scales-turn', { rotateY: 360, duration: 10000, loop: true, ease: 'linear' })`.
  - Mouse parallax: mousemove listener updates target CSS variables (`--mouse-x`, `--mouse-y`) interpolated smoothly with Anime.js `animate()` or `utils.lerp()`.

---

### c. SVG line-draw intro and drawable timelines on Verdict and Docket pages (`createDrawable` + `onScroll`)
- **Verdict**: **FULLY POSSIBLE**
- **Effort**: **S**
- **Documentation Citation**: [createDrawable Docs](https://animejs.com/documentation/svg/createdrawable), [onScroll Docs](https://animejs.com/documentation/events/onscroll)
- **Technical Mechanism**:
  ```ts
  import { animate, svg, onScroll } from 'animejs';
  // createDrawable returns an Array of Proxied SVG elements exposing the animatable 'draw' property
  const [ drawable ] = svg.createDrawable('#hearing-path');
  animate(drawable, {
    draw: ['0 0', '0 1'],
    ease: 'linear',
    autoplay: onScroll({
      target: '#timeline-container',
      sync: true,
      enter: 'top 80%',
      leave: 'bottom 40%'
    })
  });
  ```
  On Verdicts, the Perception Gap gauge needle and score lines use `svg.createDrawable` with `sync: 'play'` to animate when scrolled into view.

---

### d. Shape morph or motion path use cases (only if genuinely useful)
- **Verdict**: **POSSIBLE WITH CHANGES**
- **Effort**: **S**
- **Documentation Citation**: [morphTo Docs](https://animejs.com/documentation/svg/morphto), [createMotionPath Docs](https://animejs.com/documentation/svg/createmotionpath)
- **Analysis & Limitation**:
  - Anime.js v4 provides `svg.morphTo(targetShape, precision)` and `svg.createMotionPath(path, offset)`.
  - However, `rules.md` explicitly mandates: *"Tone: dignified. No jokes, emojis or celebratory effects in the UI."*
  - **Verdict with Changes**: Do NOT add flashy shape morphs across case cards or decorative flying elements. Restrict `morphTo` and `createMotionPath` exclusively to:
    1. Subtle transition of the Perception Gap needle indicator between neutral and active states.
    2. A gentle curved arc path for the optional voting token when dropped onto the balance scale pan.
    If no dignified aesthetic benefit is gained, omit shape morphing entirely to preserve visual gravitas.

---

### e. Live Scales of Public Opinion (spring-driven, data-bound, SSE updates)
- **Verdict**: **FULLY POSSIBLE**
- **Effort**: **M**
- **Documentation Citation**: [Spring Easing Docs](https://animejs.com/documentation/easings/spring), [Animation Parameters](https://animejs.com/documentation/animation/tween-parameters/ease)
- **Technical Mechanism**:
  - API Verification: Anime.js v4 uses `spring({ bounce, duration })` or physics `spring({ mass, stiffness, damping, velocity })` passed to `ease` (NOT `createSpring`).
  - Mathematical formulation:
    - `total = agree + partial + disagree`
    - `effectiveAgree = agree + (partial * 0.5)`
    - `effectiveDisagree = disagree + (partial * 0.5)`
    - `ratio = total > 0 ? (effectiveAgree - effectiveDisagree) / total : 0` (range `-1.0` to `+1.0`)
    - `targetAngle = ratio * -18` (degrees; Agree tilts counter-clockwise, lowering left pan)
    - `panDelta = Math.sin(degToRad(targetAngle)) * beamHalfWidth`
  - Real-time Animation:
    ```ts
    animate(beamRef.current, {
      rotate: targetAngle,
      ease: spring({ bounce: 0.25, duration: 750 })
    });
    animate(leftPanRef.current, {
      translateY: -panDelta,
      ease: spring({ bounce: 0.25, duration: 750 })
    });
    animate(rightPanRef.current, {
      translateY: panDelta,
      ease: spring({ bounce: 0.25, duration: 750 })
    });
    ```
  - When SSE `/polls/{id}/stream` delivers vote count updates, the springs automatically adjust smoothly from their current values without animation restarts.

---

### f. Optional drag-to-vote token with accessible fallback
- **Verdict**: **POSSIBLE WITH CHANGES**
- **Effort**: **M**
- **Documentation Citation**: [Draggable Docs](https://animejs.com/documentation/draggable), [Draggable Settings](https://animejs.com/documentation/draggable/draggable-settings)
- **Analysis & Accessibility Requirements**:
  - `createDraggable('#vote-token', { container: '#drop-zone', releaseEase: spring({ bounce: 0.4 }), onRelease: (self) => checkDrop(self) })` is fully functional in Anime.js v4.
  - However, drag-and-drop introduces severe accessibility barriers for keyboard users, screen readers, and mobile touch interactions (where drag gestures conflict with page scrolling).
  - **Required Architecture**:
    1. Primary UI: Accessible HTML `<button>` or `<input type="radio">` options ("Agree", "Partly agree", "Disagree") with clear focus rings and `aria-pressed` / `aria-checked` attributes.
    2. Desktop Progressive Enhancement: If pointer device is mouse (`(pointer: fine)`), display the drag token as an optional visual shortcut.
    3. Dropping the token into the left or right pan triggers the exact same `onVote(choice)` handler as clicking the button.
    4. Automatically disable drag functionality when `prefers-reduced-motion` is active or viewport width is `< 768px`.

---

### g. Scroll-synced storytelling on Home (three-story section) without GSAP ScrollTrigger
- **Verdict**: **POSSIBLE WITH CHANGES**
- **Effort**: **M**
- **Documentation Citation**: [onScroll Synchronisation Modes](https://animejs.com/documentation/events/onscroll/scrollobserver-synchronisation-modes), [ScrollObserver Settings](https://animejs.com/documentation/events/onscroll/scrollobserver-settings)
- **Analysis of Pinning**:
  - GSAP ScrollTrigger includes an imperative DOM-pinning engine (`pin: true`) that alters layout styles and injects spacing wrappers.
  - Anime.js v4 `onScroll()` is a pure **Scroll Observer**; it synchronizes animations with scroll progress (`sync: true`), but does **NOT** pin DOM elements or alter page layout flow.
  - **Solution / Alternative**: Use modern CSS `position: sticky` with top offsets and container scroll height:
    ```html
    <div class="h-[300vh] relative"> <!-- Scroll runway -->
      <div class="sticky top-24 h-[80vh] flex flex-col justify-center"> <!-- Pinned viewport -->
        <ScalesStoryStage />
      </div>
    </div>
    ```
    Anime.js `onScroll` observes the container's scroll progress (`0.0` to `1.0`), smoothly tilting the scales toward Court (0%–33%), Media (33%–66%), and Public (66%–100%) as the user scrolls. This approach is more robust than GSAP DOM pinning, eliminates layout thrashing, and is naturally responsive.

---

### h. Count-up numbers, gauge needles, animated bars
- **Verdict**: **FULLY POSSIBLE**
- **Effort**: **S**
- **Documentation Citation**: [JS Object Properties](https://animejs.com/documentation/animation/animatable-properties/javascript-object-properties), [onScroll Docs](https://animejs.com/documentation/events/onscroll)
- **Technical Mechanism**:
  - Numerical count-up:
    ```ts
    const counter = { value: 0 };
    animate(counter, {
      value: targetValue,
      round: 1, // integer rounding
      duration: 1200,
      ease: 'outExpo',
      onUpdate: () => { displayRef.current.textContent = counter.value.toLocaleString(); },
      autoplay: onScroll({ target: displayRef.current, enter: 'bottom 90%' })
    });
    ```
  - Gauge needles: `animate(needleRef.current, { rotate: [startAngle, targetAngle], ease: spring({ bounce: 0.2 }) })`.
  - Animated bars: `animate(barRef.current, { scaleX: [0, percentage / 100], transformOrigin: '0% 50%', duration: 800, ease: 'outCubic' })` (strictly animating `transform`, adhering to performance rules).

---

### i. Reduced-motion and mobile behaviour using `createScope` `mediaQueries`
- **Verdict**: **FULLY POSSIBLE**
- **Effort**: **S**
- **Documentation Citation**: [Scope MediaQueries Docs](https://animejs.com/documentation/scope/scope-parameters/mediaqueries), [Scope Docs](https://animejs.com/documentation/scope)
- **Technical Mechanism**:
  ```ts
  createScope({
    root: containerRef,
    mediaQueries: {
      reduceMotion: '(prefers-reduced-motion: reduce)',
      isMobile: '(max-width: 768px)'
    }
  }).add(self => {
    const { reduceMotion, isMobile } = self.matches;
    if (reduceMotion) {
      // Immediately render final static state; cancel all loops
      utils.set('.animated-element', { opacity: 1, transform: 'none' });
      return;
    }
    animate('.animated-element', {
      x: isMobile ? 20 : 100,
      duration: isMobile ? 400 : 800
    });
  });
  ```
  When the user's OS accessibility setting or browser viewport changes, Anime.js automatically reverts the previous animations and executes the matching branch.

---

### j. Compatibility with Next.js 15, React 19, server vs client components, StrictMode double-mount, and cleanup via `scope.revert()`
- **Verdict**: **FULLY POSSIBLE**
- **Effort**: **M**
- **Documentation Citation**: [Using with React](https://animejs.com/documentation/getting-started/using-with-react), [Scope Revert](https://animejs.com/documentation/scope/scope-methods/revert)
- **Technical Mechanism**:
  - **Server Components**: Next.js 15 App Router defaults to React Server Components (RSC). Animation code must live inside components marked with `"use client";`. Server components handle SSR data fetching and pass pre-rendered data as props to client motion components.
  - **React 19 StrictMode**: In development mode, React 19 mounts, unmounts, and remounts components to detect side effects.
  - **Cleanup via `scope.revert()`**: By creating a scope via `createScope({ root })` and returning `() => scope.current?.revert()` from `useEffect`, all animations, timers, draggables, scroll observers, and event listeners attached to the DOM subtree are cleanly cancelled and reset. No orphaned requestAnimationFrame loops or memory leaks occur.

---

### k. Coexistence with Framer Motion (page transitions) and with optional React Three Fiber
- **Verdict**: **FULLY POSSIBLE**
- **Effort**: **S**
- **Documentation Citation**: [Adapters Docs](https://animejs.com/documentation/adapters/threejs-adapter), [Using with React](https://animejs.com/documentation/getting-started/using-with-react)
- **Boundary Separation**:
  - **Framer Motion**: Confined exclusively to page-level transitions (`<AnimatePresence mode="wait">` in `layout.tsx` / `template.tsx`) and standard modal/dialog enter/exit transitions.
  - **Anime.js v4**: Confined to within-component micro-interactions, SVG line drawing, timelines, spring gauges, and scroll choreography.
  - **React Three Fiber (P1)**: Lazy-loaded behind `NEXT_PUBLIC_ENABLE_3D` via `next/dynamic({ ssr: false })`. Inside R3F, 3D mesh rotations can be handled natively in `useFrame()` or using Anime.js v4's dedicated Three.js adapter (`animejs/dist/modules/adapters/three.js`). Neither library collides because Framer Motion operates on React tree DOM nodes while Anime.js operates on scoped refs.

---

### l. Bundle size impact and which modules to import
- **Verdict**: **FULLY POSSIBLE**
- **Effort**: **S**
- **Documentation Citation**: [Module Imports Docs](https://animejs.com/documentation/getting-started/module-imports)
- **Comparison & Bundle Footprint**:
  - **GSAP Stack** (`gsap`, `@gsap/react`, `ScrollTrigger`, `Draggable`): ~45–55 KB minified + gzipped, plus proprietary licensing considerations.
  - **Anime.js v4**: ~10–14 KB minified + gzipped for the entire library; fully tree-shakeable via ES modules; MIT licensed.
  - **Module Import Strategy**:
    Import from root `'animejs'` (Next.js 15 Turbopack / Webpack performs tree-shaking automatically):
    ```ts
    import { animate, createTimeline, createScope, spring, onScroll, svg, stagger, utils, createDraggable } from 'animejs';
    ```
    Or import from specific subpaths when fine-grained isolation is desired:
    `animejs/animation`, `animejs/timeline`, `animejs/scope`, `animejs/svg`, `animejs/events`, `animejs/draggable`, `animejs/easings`, `animejs/utils`.
  - **Net Result**: Migrating from GSAP to Anime.js v4 saves ~35 KB of JavaScript per page load.

---

### m. Requirements in the four docs that are NOT fully possible with the current stack or code
- **Verdict**: **POSSIBLE WITH CHANGES**
- **Effort**: **M**
- **Identified Items (Unrelated to Anime.js)**:
  1. **Groq Free Plan Ingestion (40–50 min)**: Mentioned in `architecture.md` Section 9. Free tier rate pacing causes timeouts. *Mitigation*: Architecture already prescribes setting `LLM_PROVIDER=anthropic` or `openai` for production ingestion, and using offline pre-seeded drafts (`seeds/cases.yaml`) for instant demo loading.
  2. **Automated Cause-List Scraping across all Indian courts**: Many district and high court cause lists employ CAPTCHAs or Cloudflare bot blocks, preventing live agent scraping. *Mitigation*: Already handled in PRD/Architecture by checking `robots.txt` and falling back to cached bundles in `fixtures/collected/`.
  3. **Real-time SSE through edge serverless proxies**: SSE connections (`/polls/{id}/stream`) held open through serverless proxies can hit connection limits or timeout buffers. *Mitigation*: Docs require a 10s client polling fallback if SSE disconnects.
  4. **GSAP ScrollTrigger `pin: true`**: As established in item (g), Anime.js does not feature built-in DOM element pinning. *Mitigation*: Replaced with native CSS `position: sticky`.

---

## 5. Contradictions & Gaps Between Docs and Code

1. **Animation Engine Discrepancy**:
   - `rules.md` (lines 51–56), `architecture.md` (Section 8 & 10), and `prompts.md` (Prompts 6, 8, Optional A) explicitly prescribe GSAP, `@gsap/react`, and GSAP ScrollTrigger.
   - However, neither GSAP nor Anime.js is installed in `frontend/package.json`.
2. **Spring API Naming**:
   - The user proposal references `createSpring`.
   - Real Anime.js v4 API: The function is exported as `spring` (e.g. `import { spring } from 'animejs'`), which generates an easing function passed to the `ease` parameter. There is no function named `createSpring`.
3. **Route Paths**:
   - Current frontend code has `src/app/cases/[slug]`.
   - `prd.md` Section 5.3 and `architecture.md` Section 3 Row 8 require `/verdicts/[slug]` with a redirect from `/cases/*`.
4. **Database Configuration**:
   - `backend/app/core/config.py` defaults to `sqlite+aiosqlite:///./hetu.db`.
   - `architecture.md` Section 3 Row 10 mandates "Postgres everywhere" and eliminating SQLite defaults.
5. **Poll Creation Restrictions**:
   - `prd.md` Section 2 non-negotiables state polls can only exist on decided, published cases.
   - Current backend lacks the `0002_living_platform.py` migration and database constraint enforcing this check.
6. **Character Limit on Rules**:
   - `rules.md` line 3: "Keep this file under 12,000 characters." Current file length is 8,516 characters; updating it to Anime.js v4 easily complies with this limit.

---

## 6. Risks, Assumptions, and Open Questions

### Risks
1. **CSS Sticky Stacking Contexts**: Using CSS `position: sticky` for scroll-synced storytelling requires that no ancestor elements possess `overflow: hidden`, which can silently break sticky scrolling.
2. **Draggable Touch Conflicts**: Drag-to-vote on mobile touch screens may conflict with native vertical scroll gestures unless touch-action styles (`touch-action: pan-y`) and drag thresholds are carefully calibrated.
3. **Double-Mounting in Development**: If Anime.js instances are initialized without `createScope` cleanup, React 19 StrictMode will mount duplicate timeline tweens, causing jumpy animations.

### Assumptions
1. Framer Motion will be retained strictly for route transitions and modal animations.
2. Anime.js v4 (`npm i animejs@^4.0.0`) will be installed as the primary animation package.
3. Live Scales tilt calculation will treat "Partly agree" as an equal 50/50 split between Agree and Disagree.
4. If the user prefers reduced motion, animations will immediately resolve to their final rest positions with zero looping.

### Open Questions (7 Total)
1. **Live Scales Resting State**: If a poll has zero votes recorded (`n = 0`), should the scales rest perfectly horizontal (0° tilt), or display an initial neutral visual state?
2. **Mobile Drag-to-Vote**: On mobile viewports (< 768px), should the draggable vote token be hidden/disabled to avoid scrolling interference, showing only the accessible tap buttons?
3. **Lenis Smooth Scroll**: Since Anime.js v4 handles scroll-sync natively without requiring smooth scroll interpolation, should Lenis be omitted entirely to minimize bundle size, or retained strictly on `/` and `/jan-mat`?
4. **Import Style**: Do you prefer root module imports (`import { animate, createScope } from 'animejs'`) which Turbopack tree-shakes, or subpath imports (`import { animate } from 'animejs/animation'`)?
5. **Report Artifact Persistence**: Should this file `ANIMEJS_FEASIBILITY_REPORT.md` remain at the repo root permanently as architectural documentation?
6. **SVG Artwork Sourcing**: For the Scales Hero and Lady Justice reveal, should we craft clean, bespoke inline SVGs in `public/art/` with standard IDs (`#beam`, `#pan-left`, `#pan-right`, `#blindfold`, `#eyes`)?
7. **Comment Moderation UX**: When a user submits a comment that triggers the profanity/contempt moderation hold, should the UI optimistically show the comment with a "Pending Review" badge to the author, or display a toast notice while keeping it hidden?

---

## 7. Proposed Order of Work & Effort Estimate

| Step | Phase | Task Description | Effort | Dependencies |
|---|---|---|---|---|
| **1** | B.1 | **Documentation Updates**: Update `rules.md`, `prd.md`, `architecture.md`, `prompts.md` per Section 2. Keep `rules.md` under 12,000 chars. | **S** (1-2 hrs) | Approval |
| **2** | B.2 | **Dependencies & Tooling**: Add `animejs`, `framer-motion`, `lucide-react` to `frontend/package.json`. Verify clean install. | **S** (30 mins) | Step 1 |
| **3** | B.3 | **Database & Models (Prompt 1)**: Apply Alembic `0002_living_platform` for hearings, polls, votes, comments. Enforce decided+published constraint. | **M** (3-4 hrs) | Step 1 |
| **4** | B.4 | **Backend Poll & Vote APIs (Prompt 3)**: Implement `services/voter.py`, `services/polls.py`, `services/moderation.py`, SSE vote stream. | **M** (4-5 hrs) | Step 3 |
| **5** | B.5 | **Motion Primitives (`components/motion/`)**: Build `ScalesHero.tsx`, `LadyJusticeReveal.tsx`, `CountUp.tsx`, and `DrawLine.tsx` using `createScope` and `revert()`. | **M** (4-5 hrs) | Step 2 |
| **6** | B.6 | **Live Scales of Public Opinion Component**: Build `LiveScales.tsx` in `components/jan-mat/` with `spring()` physics, Agree/Disagree beam tilt, and accessible button/token voting. | **M** (3-4 hrs) | Steps 4, 5 |
| **7** | B.7 | **Page Refactoring (Prompts 6, 7, 8, 9)**: Assemble Home page with sticky storytelling, Live Docket with draw-line timeline, Jan Mat with Lady Justice reveal, and rename `/cases` to `/verdicts`. | **L** (6-8 hrs) | Steps 5, 6 |
| **8** | B.8 | **Verification & Testing**: Run `pytest`, `ruff`, `npm run typecheck`, `npm run lint`, accessibility axe audit, and reduced-motion tests. | **M** (3-4 hrs) | Step 7 |

**Total Estimated Effort**: ~25–32 engineering hours.
