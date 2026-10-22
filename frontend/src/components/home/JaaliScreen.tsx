/**
 * The carved screen in front of Lady Justice: two halves of a jaali meeting at a pointed arch.
 * As `--seq` (scroll progress, set by ScrollSequence) rises, the halves slide apart and the
 * arch widens. Transform only, so it stays on the compositor.
 */
const HALF = "M0 0H720V860H0Z M488 900V320C488 196 596 104 720 54V900Z";
const EDGE = "M488 900V320C488 196 596 104 720 54";
const OUTER = "M468 900V316C468 182 584 84 720 30";
// The screen's frame behind the two halves, cut to the arch at full opening. It fills the
// space above the apex that opens up as the halves slide apart.
const FRAME = "M0 0H1440V860H0Z M243 900V320C243 200 470 130 720 110C970 130 1197 200 1197 320V900Z";
const FRAME_EDGE = "M243 900V320C243 200 470 130 720 110C970 130 1197 200 1197 320V900";

function Half({ side }: { side: "left" | "right" }) {
  const left = side === "left";
  return (
    <div
      className={`absolute inset-y-0 w-1/2 ${left ? "left-0" : "right-0"}`}
      style={{ transform: `translateX(calc(var(--seq) * ${left ? "-" : ""}34%))` }}
    >
      <svg
        viewBox="0 0 720 860"
        preserveAspectRatio="xMaxYMid slice"
        className={`h-full w-full ${left ? "" : "-scale-x-100"}`}
        aria-hidden="true"
        focusable="false"
      >
        <path d={HALF} fillRule="evenodd" style={{ fill: "var(--color-stone-deep)" }} />
        <path d={HALF} fillRule="evenodd" fill="url(#jaali)" />
        <path d={OUTER} fill="none" strokeWidth="1" style={{ stroke: "var(--color-press)", strokeOpacity: 0.4 }} />
        <path d={EDGE} fill="none" strokeWidth="3" style={{ stroke: "var(--color-gold)" }} />
      </svg>
    </div>
  );
}

export function JaaliScreen() {
  return (
    <div className="pointer-events-none absolute inset-0" aria-hidden="true">
      <svg viewBox="0 0 1440 860" preserveAspectRatio="xMidYMid slice" className="absolute inset-0 h-full w-full" focusable="false">
        <path d={FRAME} fillRule="evenodd" style={{ fill: "var(--color-stone-deep)" }} />
        <path d={FRAME} fillRule="evenodd" fill="url(#jaali)" />
        <path d={FRAME_EDGE} fill="none" strokeWidth="3" style={{ stroke: "var(--color-gold)" }} />
      </svg>
      <Half side="left" />
      <Half side="right" />
    </div>
  );
}
