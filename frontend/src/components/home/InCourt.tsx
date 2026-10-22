import Link from "next/link";

import { SectionHead } from "@/components/home/SectionHead";
import type { DocketHighlightsView, ListingView } from "@/lib/api";
import { benchLabel, longDay, parties } from "@/lib/docket";

function Hearing({ title, why, l }: { title: string; why: string | null; l: ListingView }) {
  return (
    <li className="grid gap-x-6 gap-y-1 border-t border-gold-line px-5 py-5 first:border-t-0 md:grid-cols-[14rem_1fr_auto] md:items-center md:px-7">
      <span>
        <span className="block font-serif text-xl text-ivory">{longDay(l.list_date)}</span>
        <span className="text-sm text-ivory-muted">
          {l.court ?? "Courtroom to be assigned"}
          {l.sitting_time && ` · ${l.sitting_time}`}
          {l.tentative && " · tentative"}
        </span>
      </span>
      <span>
        <span className="block font-serif text-lg text-ivory">{title}</span>
        <span className="block text-sm text-ivory-muted">{parties(l)}</span>
        {why && <span className="mt-1 block text-xs uppercase tracking-[0.14em] text-gold">{why}</span>}
      </span>
      <span className="text-sm text-ivory-muted md:text-right">Item {l.item_no}</span>
    </li>
  );
}

/** The coming week in the Supreme Court: followed matters and Constitution or larger benches. */
export function InCourt({ highlights }: { highlights: DocketHighlightsView }) {
  const { tracked, notable, next_day: next } = highlights;
  const hearings = [
    ...tracked
      .filter((t) => t.next_listing)
      .map((t) => ({ key: t.id, title: t.title, why: "Followed by Hetu", l: t.next_listing as ListingView })),
    ...notable.map((l) => ({ key: `${l.list_date}-${l.case_number}`, title: l.case_number, why: benchLabel(l.bench_size), l })),
  ].slice(0, 5);

  return (
    <section aria-labelledby="incourt" className="border-t border-gold-line bg-surface px-4 py-20 sm:px-8 sm:py-28 lg:px-12">
      <div className="mx-auto max-w-[90rem]">
        <SectionHead no="04" id="incourt" kicker="Live Docket · Supreme Court of India" title="In court this week.">
          {next
            ? `${longDay(next.list_date)}: ${next.matters.toLocaleString("en-IN")} matters before ${next.courts} courtrooms${next.tentative ? " (tentative list)" : ""}.`
            : "The court's lists appear here once they are read."}
        </SectionHead>

        {hearings.length > 0 ? (
          <ol className="border border-gold-line bg-ink">
            {hearings.map(({ key, ...h }) => (
              <Hearing key={key} {...h} />
            ))}
          </ol>
        ) : (
          <p className="border border-dashed border-gold-line bg-ink p-8 text-center text-ivory-muted">
            No Constitution Bench or followed matter is listed in the coming days.
          </p>
        )}

        <div className="mt-8 flex flex-wrap items-center gap-4">
          <Link href="/live-docket" className="btn-seal">
            Find a hearing
          </Link>
          <span className="text-sm text-ivory-muted">Search every listed matter by case number, judge or advocate.</span>
        </div>
      </div>
    </section>
  );
}
