import type { Metadata } from "next";
import Link from "next/link";

import { JaaliField } from "@/components/jaali/JaaliPatterns";
import { ErrorState } from "@/components/ui/ErrorState";
import { api, type DocketView, type ListingView, type TrackedMatterView } from "@/lib/api";
import { benchLabel, byCourt, checkedAt, EPASS_URL, longDay, parties, shortDay } from "@/lib/docket";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Live Docket — Who is in court, and when | Hetu",
  description:
    "The Supreme Court of India's cause lists, searchable by case number, judge or advocate, with courtroom, bench and sitting time.",
};

type Search = { q?: string; date?: string; criminal?: string; notable?: string; offset?: string };

const PAGE = 50;

function href(params: Search, change: Partial<Search>): string {
  const next = { ...params, ...change };
  const query = new URLSearchParams(
    Object.entries(next).filter((e): e is [string, string] => typeof e[1] === "string" && e[1] !== ""),
  );
  const text = query.toString();
  return text ? `/live-docket?${text}` : "/live-docket";
}

function Row({ l }: { l: ListingView }) {
  return (
    <li className="grid gap-x-6 gap-y-1 border-t border-gold-line px-4 py-4 sm:grid-cols-[4.5rem_1fr_auto] sm:px-6">
      <span className="font-serif text-2xl tabular-nums text-gold">{l.item_no}</span>
      <div>
        <p className="font-serif text-lg text-ivory">
          {l.case_number}
          {l.is_criminal && (
            <span className="ml-3 inline-block border border-gold-line px-2 py-0.5 align-middle font-sans text-[11px] uppercase tracking-[0.14em] text-ivory-muted">
              Criminal
            </span>
          )}
        </p>
        <p className="mt-1 text-sm text-ivory-muted">{parties(l)}</p>
        {(l.stage || l.advocates.length > 0) && (
          <p className="mt-1 text-xs text-ivory-faint">
            {l.stage && <span className="mr-3 uppercase tracking-[0.12em]">{l.stage}</span>}
            {l.advocates.length > 0 && <span>Advocates: {l.advocates.slice(0, 3).join(", ")}</span>}
          </p>
        )}
      </div>
      <a href={l.source_url} target="_blank" rel="noreferrer" className="self-start text-sm text-gold hover:text-bronze">
        Court&apos;s list ↗
      </a>
    </li>
  );
}

function Watch({ tracked, notable }: { tracked: TrackedMatterView[]; notable: ListingView[] }) {
  const items = [
    ...tracked
      .filter((t) => t.next_listing)
      .map((t) => ({ key: t.id, title: t.title, l: t.next_listing as ListingView, why: "Followed by Hetu" })),
    ...notable.map((l) => ({ key: `${l.case_number}-${l.list_date}`, title: l.case_number, l, why: benchLabel(l.bench_size) })),
  ].slice(0, 6);
  if (!items.length) return null;
  return (
    <section aria-labelledby="watch" className="mb-14">
      <h2 id="watch" className="eyebrow mb-4">
        Matters to watch
      </h2>
      <ul className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {items.map(({ key, title, l, why }) => (
          <li key={key} className="flex flex-col rounded-t-[10rem] border border-gold bg-ink px-6 pb-6 pt-16">
            <p className="text-center text-xs uppercase tracking-[0.18em] text-ivory-faint">{why}</p>
            <p className="mt-2 text-center font-serif text-xl text-ivory">{title}</p>
            <p className="mt-1 text-center text-sm text-ivory-muted">{parties(l)}</p>
            <p className="mt-4 border-t border-gold-line pt-4 text-center text-sm">
              <span className="font-semibold text-ivory">{longDay(l.list_date)}</span>
              <br />
              {l.court ?? "Courtroom to be assigned"}
              {l.sitting_time && ` · ${l.sitting_time}`} · Item {l.item_no}
              {l.tentative && <span className="block text-xs text-gold">Tentative (advance list)</span>}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Attend() {
  return (
    <aside aria-labelledby="attend" className="reverse relative overflow-hidden border border-gold-line p-7">
      <JaaliField variant="ink" className="absolute inset-x-0 top-0 h-6 w-full" />
      <h2 id="attend" className="mt-4 font-serif text-2xl">
        Attending a hearing
      </h2>
      <ol className="mt-4 flex list-decimal flex-col gap-3 pl-5 text-sm leading-relaxed text-ivory-muted">
        <li>
          Note the date, courtroom and item number. Matters are heard in item order, so a later item can start well after
          the sitting time.
        </li>
        <li>
          Get an entry pass. The Supreme Court issues visitor e-passes online through{" "}
          <a href={EPASS_URL} target="_blank" rel="noreferrer" className="text-gold underline underline-offset-4">
            SuSwagatam
          </a>
          ; carry the same photo ID you register with.
        </li>
        <li>Advance lists are tentative. Check the daily list the evening before; matters can be deleted or moved.</li>
        <li>Courtroom rules apply: silence, no recording, phones off.</li>
      </ol>
      <p className="mt-5 border-t border-gold-line pt-4 text-xs text-ivory-faint">
        Hetu lists hearings only. Pending matters have no polls or comments here.
      </p>
    </aside>
  );
}

export default async function LiveDocketPage({ searchParams }: { searchParams: Promise<Search> }) {
  const params = await searchParams;
  const offset = Number(params.offset ?? 0) || 0;
  const [docketRes, highlightsRes] = await Promise.all([
    api
      .GET("/docket", {
        params: {
          query: {
            q: params.q || undefined,
            date: params.date || undefined,
            criminal: params.criminal === "1",
            notable: params.notable === "1",
            limit: PAGE,
            offset,
          },
        },
      })
      .catch(() => ({ data: undefined })),
    api.GET("/docket/highlights").catch(() => ({ data: undefined })),
  ]);
  const docket: DocketView | undefined = docketRes.data;
  const highlights = highlightsRes.data;
  const activeDate = params.date ?? (params.q ? undefined : docket?.days[0]?.list_date);
  const activeDay = docket?.days.find((d) => d.list_date === activeDate);

  return (
    <div className="flex flex-col gap-10 py-6">
      <header className="grid gap-8 border-b border-gold-line pb-10 lg:grid-cols-[1fr_22rem] lg:items-end">
        <div>
          <p className="eyebrow">Live Docket · Supreme Court of India</p>
          <h1 className="mt-3 font-serif text-4xl leading-tight text-ivory sm:text-6xl">Who is in court, and when.</h1>
          <p className="mt-4 max-w-2xl text-base leading-relaxed text-ivory-muted">
            Every matter on the Supreme Court&apos;s published cause lists, with its courtroom, bench and sitting time. Search
            by case number, judge or advocate. Private parties are shown only by their role.
          </p>
        </div>
        <p className="text-sm text-ivory-faint lg:text-right">
          {docket?.last_checked ? `Last read from the court's lists ${checkedAt(docket.last_checked)}` : "Not read yet"}
          <br />
          Source:{" "}
          <a href="https://www.sci.gov.in/cause-list/" target="_blank" rel="noreferrer" className="text-gold underline underline-offset-4">
            sci.gov.in cause lists
          </a>
        </p>
      </header>

      {!docket ? (
        <ErrorState
          eyebrow="Live Docket"
          title="The docket could not be loaded"
          message="The Hetu service did not answer. Refresh in a moment."
        />
      ) : docket.days.length === 0 ? (
        <div className="border border-dashed border-gold-line p-10 text-center">
          <p className="font-serif text-2xl text-ivory">No cause lists have been read yet.</p>
          <p className="mt-2 text-sm text-ivory-muted">
            A curator reads the Supreme Court&apos;s published lists from the admin area. They appear here once read.
          </p>
        </div>
      ) : (
        <>
          {highlights && <Watch tracked={highlights.tracked} notable={highlights.notable} />}

          <div className="grid gap-10 lg:grid-cols-[1fr_22rem]">
            <div className="min-w-0">
              <form action="/live-docket" className="flex flex-col gap-4 border border-gold-line bg-surface p-5 sm:p-6">
                <label htmlFor="q" className="eyebrow">
                  Find a matter
                </label>
                <div className="flex flex-col gap-3 sm:flex-row">
                  <input
                    id="q"
                    name="q"
                    defaultValue={params.q}
                    placeholder="Case number, judge or advocate, e.g. SLP(Crl) 7857/2022"
                    className="min-h-11 flex-1 border border-gold-line bg-ink px-4 text-ivory placeholder:text-ivory-faint focus:border-gold focus:outline-none"
                  />
                  <button type="submit" className="btn-seal justify-center">
                    Search
                  </button>
                </div>
                <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-ivory-muted">
                  <label className="flex items-center gap-2">
                    <input type="checkbox" name="criminal" value="1" defaultChecked={params.criminal === "1"} className="accent-[var(--color-gold)]" />
                    Criminal matters only
                  </label>
                  <label className="flex items-center gap-2">
                    <input type="checkbox" name="notable" value="1" defaultChecked={params.notable === "1"} className="accent-[var(--color-gold)]" />
                    Constitution and larger benches
                  </label>
                  {params.date && <input type="hidden" name="date" value={params.date} />}
                </div>
              </form>

              <nav aria-label="Listing dates" className="mt-6 flex gap-2 overflow-x-auto pb-2">
                {docket.days.map((d) => {
                  const active = d.list_date === activeDate;
                  return (
                    <Link
                      key={d.list_date}
                      href={href({ ...params, offset: undefined }, { date: d.list_date })}
                      aria-current={active ? "date" : undefined}
                      className={`shrink-0 border px-4 py-2 text-sm ${active ? "border-gold bg-gold text-paper" : "border-gold-line text-ivory-muted hover:border-ivory"}`}
                    >
                      {shortDay(d.list_date)}
                      <span className="ml-2 tabular-nums opacity-80">{d.matters.toLocaleString("en-IN")}</span>
                      {d.tentative && <span className="ml-1 text-xs">·&nbsp;tentative</span>}
                    </Link>
                  );
                })}
                {(params.date || params.q) && (
                  <Link href="/live-docket" className="shrink-0 px-3 py-2 text-sm text-gold">
                    Clear
                  </Link>
                )}
              </nav>

              <p className="mt-4 text-sm text-ivory-muted" aria-live="polite">
                {params.q ? (
                  <>
                    {docket.total.toLocaleString("en-IN")} listings for “{params.q}”{activeDate ? ` on ${longDay(activeDate)}` : " from today"}
                  </>
                ) : (
                  activeDay && (
                    <>
                      {longDay(activeDay.list_date)}: {activeDay.matters.toLocaleString("en-IN")} matters before{" "}
                      {activeDay.courts} courtrooms{activeDay.tentative && " (tentative advance list)"}
                    </>
                  )
                )}
              </p>

              {docket.results.length === 0 ? (
                <p className="mt-6 border border-dashed border-gold-line p-8 text-center text-ivory-muted">
                  Nothing matches. Try the case number as printed, for example “W.P.(C) 77/2024”.
                </p>
              ) : (
                <div className="mt-6 flex flex-col gap-8">
                  {byCourt(docket.results).map(({ court, first, items }) => (
                    <section key={`${first.list_date}-${court}`} className="border border-gold-line bg-ink">
                      <header className="flex flex-wrap items-baseline justify-between gap-3 bg-surface px-4 py-4 sm:px-6">
                        <div>
                          <h2 className="font-serif text-2xl text-ivory">{court}</h2>
                          {first.bench.length > 0 && <p className="mt-1 text-sm text-ivory-muted">{first.bench.join(" · ")}</p>}
                        </div>
                        <p className="text-sm text-ivory">
                          {params.q && `${shortDay(first.list_date)} · `}
                          {first.sitting_time ?? first.time_note ?? (first.tentative ? "Tentative" : "")}
                          {benchLabel(first.bench_size) && (
                            <span className="ml-2 border border-gold px-2 py-0.5 text-xs text-gold">{benchLabel(first.bench_size)}</span>
                          )}
                        </p>
                      </header>
                      <ol>
                        {items.map((l) => (
                          <Row key={`${l.list_date}-${l.court}-${l.item_no}-${l.case_number}`} l={l} />
                        ))}
                      </ol>
                    </section>
                  ))}
                </div>
              )}

              {docket.total > offset + PAGE && (
                <div className="mt-8 flex justify-center">
                  <Link href={href(params, { offset: String(offset + PAGE) })} className="btn-plain">
                    Next {PAGE} matters
                  </Link>
                </div>
              )}
            </div>

            <div className="lg:sticky lg:top-28 lg:self-start">
              <Attend />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
