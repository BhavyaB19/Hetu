/**
 * SVG patterns for the jaali, the carved stone screen that frames the site. Rendered once in
 * the root layout; any SVG on the page can fill with `url(#jaali)`, `url(#jaali-fine)` or
 * `url(#jaali-ink)`. Each tile is stone with an eight-point star cut through it; the lit and
 * shaded strokes give the cut its depth.
 */
const STAR = "M36 10 L43 26 L60 22 L50 36 L60 50 L43 46 L36 62 L29 46 L12 50 L22 36 L12 22 L29 26 Z";
const CORNERS = "M0 -8 L8 0 L0 8 L-8 0 Z M72 -8 L80 0 L72 8 L64 0 Z M0 64 L8 72 L0 80 L-8 72 Z M72 64 L80 72 L72 80 L64 72 Z";
const SMALL_STAR = "M22 6 L26 16 L37 13 L31 22 L37 31 L26 28 L22 38 L18 28 L7 31 L13 22 L7 13 L18 16 Z";

export function JaaliPatterns() {
  return (
    <svg width="0" height="0" className="absolute" aria-hidden="true" focusable="false">
      <defs>
        <pattern id="jaali" width="72" height="72" patternUnits="userSpaceOnUse">
          <path style={{ fill: "var(--color-stone)" }} fillRule="evenodd" d={`M0 0H72V72H0Z ${STAR} ${CORNERS}`} />
          <path
            d={STAR}
            fill="none"
            strokeWidth="1.2"
            transform="translate(-0.6 -0.6)"
            style={{ stroke: "var(--color-stone-edge)", strokeOpacity: 0.6 }}
          />
          <path
            d={STAR}
            fill="none"
            strokeWidth="1.6"
            transform="translate(0.9 0.9)"
            style={{ stroke: "var(--color-press)", strokeOpacity: 0.4 }}
          />
        </pattern>
        <pattern id="jaali-fine" width="44" height="44" patternUnits="userSpaceOnUse">
          <path style={{ fill: "var(--color-stone-deep)" }} fillRule="evenodd" d={`M0 0H44V44H0Z ${SMALL_STAR}`} />
        </pattern>
        <pattern id="jaali-ink" width="44" height="44" patternUnits="userSpaceOnUse">
          <rect width="44" height="44" style={{ fill: "var(--color-press)" }} />
          <path style={{ fill: "#2f2924" }} fillRule="evenodd" d={`M0 0H44V44H0Z ${SMALL_STAR}`} />
        </pattern>
      </defs>
    </svg>
  );
}

/** A band or field of carved screen. `variant` picks the stone, fine or ink lattice. */
export function JaaliField({ variant = "fine", className = "" }: { variant?: "stone" | "fine" | "ink"; className?: string }) {
  const id = variant === "stone" ? "jaali" : variant === "ink" ? "jaali-ink" : "jaali-fine";
  return (
    <svg className={`pointer-events-none ${className}`} aria-hidden="true" focusable="false">
      <rect width="100%" height="100%" fill={`url(#${id})`} />
    </svg>
  );
}
