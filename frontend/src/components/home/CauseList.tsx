import Link from "next/link";

import { SectionHead } from "@/components/home/SectionHead";
import type { CaseSummary } from "@/lib/api";

/** Published verdicts set out like a court's daily cause list. */
export function CauseList({ cases }: { cases: CaseSummary[] }) {
  return (
    <section aria-labelledby="list" className="px-4 py-20 sm:px-8 sm:py-28 lg:px-12">
      <div className="mx-auto max-w-[90rem]">
        <SectionHead no="03" id="list" kicker="Cause list" title="Verdicts on the board.">
          Every case is reviewed by a person before it is published. Private individuals appear only as placeholders.
        </SectionHead>

        <ol className="border border-gold-line">
          <li aria-hidden className="hidden h-12 grid-cols-[6rem_1.6fr_1fr_13rem_10rem] items-center gap-6 bg-surface px-7 text-[11px] uppercase tracking-[0.2em] text-ivory-faint md:grid">
            <span>Item</span>
            <span>Case</span>
            <span>Court</span>
            <span>Perception gap</span>
            <span />
          </li>
          {cases.map((c, i) => (
            <li
              key={c.slug}
              className="grid gap-x-6 gap-y-2 border-t border-gold-line px-5 py-6 first:border-t-0 md:grid-cols-[6rem_1.6fr_1fr_13rem_10rem] md:items-center md:px-7 md:first:border-t"
            >
              <span className="font-serif text-3xl tabular-nums text-gold">{String(i + 1).padStart(2, "0")}</span>
              <span>
                <span className="block font-serif text-2xl text-ivory">{c.title}</span>
                {c.summary && <span className="mt-1 block text-sm leading-relaxed text-ivory-muted">{c.summary}</span>}
                {c.is_illustrative && <span className="mt-2 inline-block text-xs text-gold">Illustrative demo</span>}
              </span>
              <span className="text-sm text-ivory-muted">{c.court ?? c.category}</span>
              <span className="flex items-center gap-3">
                <span className="font-serif text-3xl tabular-nums">{c.gap_score?.toFixed(1) ?? "—"}</span>
                {c.gap_score !== null && (
                  <span className="h-1.5 flex-1 bg-track" aria-hidden>
                    <span className="block h-full bg-gold" style={{ width: `${c.gap_score}%` }} />
                  </span>
                )}
              </span>
              <Link href={`/verdicts/${c.slug}`} className="font-semibold text-gold hover:text-bronze md:justify-self-end">
                Open the record →
              </Link>
            </li>
          ))}
          <li className="grid border-t border-gold-line px-5 py-5 text-sm text-ivory-faint md:grid-cols-[6rem_1fr] md:gap-6 md:px-7">
            <span className="font-serif text-3xl tabular-nums">{String(cases.length + 1).padStart(2, "0")}</span>
            <span className="self-center">More verdicts are under review and appear here once published.</span>
          </li>
        </ol>
      </div>
    </section>
  );
}
