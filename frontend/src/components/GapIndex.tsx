import type { GapView } from "@/lib/api";
import { pct } from "@/lib/format";

/** The headline score, with each component's value, weight and reason one click away. */
export function GapIndex({ gap }: { gap: GapView }) {
  return (
    <div className="card flex flex-col gap-4 p-6">
      <p className="eyebrow">Perception Gap Index</p>
      <p className="flex items-baseline gap-2">
        <span className="text-7xl font-semibold text-gold">{Math.round(gap.score)}</span>
        <span className="text-lg text-ivory-muted">/100</span>
      </p>
      <p className="text-sm text-ivory-muted">
        How far media and public narratives drift from what the court found. 0 means they match the judgment.
      </p>
      <details className="group" open>
        <summary className="cursor-pointer list-none text-sm text-gold hover:text-bronze">
          <span className="group-open:hidden">Show why ▸</span>
          <span className="hidden group-open:inline">Why this score ▾</span>
        </summary>
        <ul className="mt-4 flex flex-col gap-4">
          {gap.components.map((c) => (
            <li key={c.key}>
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span className="text-ivory">{c.label}</span>
                <span className="text-ivory-muted">
                  +{c.contribution.toFixed(1)} pts · {pct(c.value)} gap × {pct(c.weight)} weight
                </span>
              </div>
              <div
                className="mt-1.5 h-2 rounded-full bg-track"
                role="img"
                aria-label={`${c.label}: ${pct(c.value)} divergence`}
              >
                <div className="bar h-2 bg-gold" style={{ width: pct(c.value) }} />
              </div>
              <p className="mt-1.5 text-xs leading-relaxed text-ivory-muted">{c.explanation}</p>
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
