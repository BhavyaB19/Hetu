import { SectionHead } from "@/components/home/SectionHead";
import type { CaseSummary, GapView } from "@/lib/api";

const TICKS = Array.from({ length: 21 }, (_, i) => i * 5);

/** One etched 0 to 100 scale. Every published case is pinned on it; the featured case leads. */
export function GapMeasure({ cases, featured, gap }: { cases: CaseSummary[]; featured: CaseSummary; gap: GapView | null }) {
  const pinned = cases.filter((c) => c.gap_score !== null);

  return (
    <section aria-labelledby="gap" className="border-y border-gold-line bg-surface px-4 py-20 sm:px-8 sm:py-28 lg:px-12">
      <div className="mx-auto max-w-[90rem]">
        <SectionHead no="02" id="gap" kicker="The Perception Gap Index" title="One scale for every case.">
          0 means the media and the public told the court&apos;s story. 100 means they told a different one.
        </SectionHead>

        <figure>
          <div className="relative mx-2 h-40" role="img" aria-label={pinned.map((c) => `${c.title}: ${c.gap_score?.toFixed(1)}`).join("; ")}>
            <div className="absolute inset-x-0 top-[3.75rem] h-0.5 bg-gold-line" />
            {TICKS.map((t) => (
              <span
                key={t}
                className={`absolute w-px bg-ivory-faint ${t % 10 === 0 ? "top-11 h-9" : "top-[3.25rem] h-5 opacity-60"}`}
                style={{ left: `${t}%` }}
              />
            ))}
            {[0, 20, 40, 60, 80, 100].map((t) => (
              <span
                key={t}
                className="absolute top-[5.75rem] text-sm tabular-nums text-ivory-faint"
                style={{ left: `${t}%`, transform: t === 100 ? "translateX(-100%)" : t === 0 ? undefined : "translateX(-50%)" }}
              >
                {t}
              </span>
            ))}
            {pinned.map((c) => {
              const lead = c.slug === featured.slug;
              return (
                <span
                  key={c.slug}
                  className="absolute top-0 flex -translate-x-1/2 flex-col items-center"
                  style={{ left: `${c.gap_score}%` }}
                  title={c.title}
                >
                  <span className={`font-serif tabular-nums ${lead ? "text-3xl text-gold" : "text-lg text-ivory-muted"}`}>
                    {c.gap_score?.toFixed(1)}
                  </span>
                  <span className={`mt-2 rotate-45 ${lead ? "h-4 w-4 bg-gold" : "h-2.5 w-2.5 bg-ivory-muted"}`} />
                </span>
              );
            })}
            <span className="absolute left-0 top-[7.5rem] text-xs uppercase tracking-[0.18em] text-ivory-muted">Aligned with the record</span>
            <span className="absolute right-0 top-[7.5rem] text-xs uppercase tracking-[0.18em] text-ivory-muted">Far from the record</span>
          </div>
          <figcaption className="sr-only">Perception Gap Index for each published case, on a scale of 0 to 100.</figcaption>
        </figure>

        {gap && (
          <dl className="mt-12 grid border border-gold-line sm:grid-cols-2 lg:grid-cols-4">
            {gap.components.map((c) => (
              <div key={c.key} className="border-gold-line p-6 not-last:border-b sm:[&:nth-child(odd)]:border-r lg:border-b-0 lg:not-last:border-r">
                <p className="font-serif text-4xl text-ivory">
                  {Math.round(c.weight * 100)}
                  <span className="text-lg text-ivory-faint">%</span>
                </p>
                <dt className="mt-2 text-[0.95rem] font-semibold">{c.label}</dt>
                <dd className="mt-1 text-sm leading-relaxed text-ivory-muted">{c.explanation}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>
    </section>
  );
}
