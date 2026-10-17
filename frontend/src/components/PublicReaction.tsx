import type { PublicView } from "@/lib/api";
import { SENTIMENT, pct } from "@/lib/format";

const RADIUS = 60;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const GAP = 2; // px of surface between segments

type SentimentKey = keyof typeof SENTIMENT;

function Donut({ data, total }: { data: PublicView["sentiment"]; total: number }) {
  let offset = 0;
  return (
    <svg viewBox="0 0 160 160" className="h-44 w-44 shrink-0" role="img" aria-label="Public reaction by stance">
      <g transform="rotate(-90 80 80)">
        {data.map((s) => {
          const length = s.share * CIRCUMFERENCE;
          const segment = (
            <circle
              key={s.key}
              cx="80"
              cy="80"
              r={RADIUS}
              fill="none"
              stroke={SENTIMENT[s.key as SentimentKey].color}
              strokeWidth="18"
              strokeDasharray={`${Math.max(length - GAP, 0)} ${CIRCUMFERENCE}`}
              strokeDashoffset={-offset}
            >
              <title>{`${SENTIMENT[s.key as SentimentKey].label}: ${s.count} (${pct(s.share)})`}</title>
            </circle>
          );
          offset += length;
          return s.count > 0 ? segment : null;
        })}
      </g>
      <text x="80" y="78" textAnchor="middle" className="fill-ivory text-[26px] font-semibold">
        {total}
      </text>
      <text x="80" y="98" textAnchor="middle" className="fill-ivory-muted text-[11px]">
        reactions
      </text>
    </svg>
  );
}

/** Aggregate public stance and recurring themes. No individual is profiled. */
export function PublicReaction({ data }: { data: PublicView }) {
  if (data.total === 0) {
    return <p className="card p-6 text-sm text-ivory-muted">No public reactions were collected for this case.</p>;
  }
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="card flex flex-col items-center gap-6 p-6 sm:flex-row">
        <Donut data={data.sentiment} total={data.total} />
        <ul className="flex w-full flex-col gap-3">
          {data.sentiment.map((s) => (
            <li key={s.key} className="flex items-center gap-3 text-sm">
              <span className="h-3 w-3 shrink-0 rounded-sm" style={{ background: SENTIMENT[s.key as SentimentKey].color }} />
              <span className="flex-1 text-ivory">{SENTIMENT[s.key as SentimentKey].label}</span>
              <span className="text-ivory-muted">
                {pct(s.share)} <span className="text-ivory-faint">({s.count})</span>
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="card flex flex-col gap-4 p-6">
        <h3 className="text-sm text-ivory-muted">Top themes (share of reactions)</h3>
        <ul className="flex flex-col gap-3">
          {data.themes.slice(0, 6).map((t) => (
            <li key={t.key} className="grid grid-cols-[minmax(0,10rem)_1fr_2.5rem] items-center gap-3 text-sm">
              <span className="truncate text-ivory" title={t.key}>
                {t.key}
              </span>
              <div className="h-2 rounded-full bg-track" title={`${t.key}: ${t.count} reactions`}>
                <div className="bar h-2 bg-gold" style={{ width: pct(t.share) }} />
              </div>
              <span className="text-right text-ivory-muted">{pct(t.share)}</span>
            </li>
          ))}
        </ul>
      </div>

      <details className="card p-6 lg:col-span-2">
        <summary className="cursor-pointer text-sm text-gold hover:text-bronze">
          Read the {data.total} anonymized reactions
        </summary>
        <ul className="mt-4 grid gap-3 md:grid-cols-2">
          {data.reactions.map((r, i) => (
            <li key={i} className="rounded-md border border-gold-line p-3 text-sm">
              <p className="text-ivory">{r.text}</p>
              <p className="mt-2 flex items-center gap-2 text-xs text-ivory-muted">
                <span className="h-2 w-2 rounded-full" style={{ background: SENTIMENT[r.sentiment].color }} />
                {SENTIMENT[r.sentiment].label} · {r.platform}
              </p>
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}
