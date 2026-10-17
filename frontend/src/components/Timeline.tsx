import { EvidenceLink } from "@/components/EvidenceLink";
import type { TimelineEventView } from "@/lib/api";
import { date, pct } from "@/lib/format";

function WeightBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="grid grid-cols-[3.5rem_1fr_2.5rem] items-center gap-2 text-xs text-ivory-muted" title={`${label}: ${pct(value)}`}>
      <span>{label}</span>
      <div className="h-1.5 rounded-full bg-track">
        <div className="bar h-1.5" style={{ width: pct(value), background: color }} />
      </div>
      <span className="text-right">{pct(value)}</span>
    </div>
  );
}

/** Numbered stepper of key events, each with how much the court vs the media weighed it. */
export function Timeline({ events }: { events: TimelineEventView[] }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-5 text-xs text-ivory-muted">
        <span className="flex items-center gap-2">
          <span className="h-2 w-4 rounded-sm bg-viz-1" /> Court: how central to the judgment
        </span>
        <span className="flex items-center gap-2">
          <span className="h-2 w-4 rounded-sm bg-viz-3" /> Media: share of articles covering it
        </span>
      </div>
      <ol className="grid gap-4 md:grid-cols-5">
        {events.map((event, i) => (
          <li key={i} className="card flex flex-col gap-3 p-4">
            <div className="flex items-center gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-gold text-sm text-gold">
                {i + 1}
              </span>
              <span className="text-xs text-ivory-muted">{event.date ? date(event.date) : "During appeal"}</span>
            </div>
            <div>
              <h3 className="font-serif text-lg leading-snug text-ivory">{event.label}</h3>
              <p className="mt-1 text-xs leading-relaxed text-ivory-muted">{event.description}</p>
            </div>
            <div className="mt-auto flex flex-col gap-1.5">
              <WeightBar label="Court" value={event.court_weight} color="var(--color-viz-1)" />
              <WeightBar label="Media" value={event.media_weight} color="var(--color-viz-3)" />
            </div>
            <EvidenceLink evidence={event.evidence} />
          </li>
        ))}
      </ol>
    </div>
  );
}
