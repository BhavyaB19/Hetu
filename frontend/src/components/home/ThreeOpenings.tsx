import Link from "next/link";
import type { ReactNode } from "react";

import { EvidenceLink } from "@/components/EvidenceLink";
import { ClaimMark, ClaimMarks, MARK_LABEL } from "@/components/home/ClaimMarks";
import { SectionHead } from "@/components/home/SectionHead";
import { JaaliField } from "@/components/jaali/JaaliPatterns";
import type { CaseView } from "@/lib/api";
import { FRAMING } from "@/lib/format";

const OUTCOME: Record<string, string> = { conviction: "Convicted", acquittal: "Acquitted", other: "Decided" };

const SENTIMENT_LABEL: Record<string, string> = {
  support_victim: "For the victim",
  against_media_bias: "Media bias",
  neutral_uncertain: "Unsure",
  support_accused: "For the accused",
};

function Opening({ no, who, title, lit, children, foot }: { no: string; who: string; title: string; lit?: boolean; children: ReactNode; foot: ReactNode }) {
  return (
    <article
      className={`relative flex min-h-[32rem] flex-col rounded-t-full border bg-ink px-6 pb-8 pt-28 sm:px-8 sm:pt-36 ${
        lit ? "border-gold shadow-[6px_6px_0_0_var(--color-gold-soft)] ring-1 ring-gold" : "border-gold-line"
      }`}
    >
      <span className="absolute left-1/2 top-12 -translate-x-1/2 font-serif text-xl text-gold sm:top-14">{no}</span>
      <p className="text-center text-xs uppercase tracking-[0.24em] text-ivory-muted">{who}</p>
      <h3 className="mb-7 mt-2 text-center font-serif text-3xl text-ivory">{title}</h3>
      {children}
      <div className="mt-auto flex items-center justify-between gap-3 border-t border-gold-line pt-5 text-sm text-ivory-muted">{foot}</div>
    </article>
  );
}

/** The featured case read through three arches: the court's record lit, media and public beside it. */
export function ThreeOpenings({ view, pollHref }: { view: CaseView; pollHref: string }) {
  const { judgment, media, public: pub, case: info } = view;
  // The article that strays furthest from the judgment shows the gap most plainly.
  const article = [...media].sort(
    (a, b) => b.claims.filter((c) => c.verdict !== "supported").length - a.claims.filter((c) => c.verdict !== "supported").length,
  )[0];
  const shares = [...pub.sentiment].sort((a, b) => b.count - a.count);

  return (
    <section aria-labelledby="three" className="relative bg-surface px-4 pb-14 pt-20 sm:px-8 lg:px-12">
      <JaaliField className="absolute inset-0 h-full w-full opacity-50" />
      <div className="relative mx-auto max-w-[90rem]">
        <SectionHead no="01" id="three" kicker={info.title} title="The same case, through three openings.">
          The court&apos;s record is the reference. The media and the public are read against it, claim by claim.
        </SectionHead>

        <div className="grid gap-8 lg:grid-cols-3 lg:gap-10">
          {judgment && (
            <Opening
              no="I"
              who="The court"
              title="What was decided"
              lit
              foot={
                <>
                  <span className="inline-flex items-center gap-2 border border-gold-line px-3 py-1.5 text-xs text-ivory">
                    <span className="lozenge" aria-hidden />
                    {OUTCOME[judgment.outcome_direction]}
                    {judgment.legal_provisions[0] && ` · ${judgment.legal_provisions[0]}`}
                  </span>
                  <Link href={`/verdicts/${info.slug}`} className="text-gold hover:text-bronze">
                    The record →
                  </Link>
                </>
              }
            >
              <p className="text-xs uppercase tracking-[0.16em] text-ivory-faint">On motive</p>
              <blockquote className="mt-2 font-serif text-xl leading-snug text-ivory">“{judgment.motive}”</blockquote>
              <div className="mt-4">
                <EvidenceLink evidence={judgment.evidence.motive} label="Judgment" />
              </div>
            </Opening>
          )}

          {article && (
            <Opening
              no="II"
              who="The media"
              title="What was reported"
              foot={
                <>
                  <span>{article.claims.length} claims</span>
                  <ClaimMarks verdicts={article.claims.map((c) => c.verdict)} />
                </>
              }
            >
              <blockquote className="font-serif text-xl leading-snug text-ivory">“{article.headline}”</blockquote>
              <p className="mt-4 text-sm text-gold">
                {article.outlet} · {FRAMING[article.framing]?.toLowerCase()} framing
              </p>
            </Opening>
          )}

          <Opening
            no="III"
            who="The public"
            title="What India felt"
            foot={
              <>
                <span>Jan Mat is open</span>
                <Link href={pollHref} className="text-gold hover:text-bronze">
                  Cast your vote →
                </Link>
              </>
            }
          >
            {pub.total > 0 ? (
              <ul className="flex flex-col gap-3">
                {shares.map((s) => (
                  <li key={s.key} className="grid grid-cols-[7.5rem_1fr_1.5rem] items-center gap-3 text-sm">
                    <span>{SENTIMENT_LABEL[s.key] ?? s.key}</span>
                    <span className="h-2.5 bg-track">
                      <span className="block h-full bg-gold" style={{ width: `${Math.round(s.share * 100)}%` }} />
                    </span>
                    <span className="text-right tabular-nums">{s.count}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="font-serif text-xl leading-snug text-ivory-muted">
                No public reactions were collected for this case. Jan Mat is where the public&apos;s story is recorded.
              </p>
            )}
            {pub.total > 0 && (
              <p className="mt-5 text-xs text-ivory-muted">{pub.total} collected reactions · Not a representative sample</p>
            )}
          </Opening>
        </div>

        <ul className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-3 text-sm text-ivory-muted">
          {(["supported", "absent", "contradicted"] as const).map((v) => (
            <li key={v} className="flex items-center gap-2">
              <ClaimMark verdict={v} />
              {MARK_LABEL[v]}
            </li>
          ))}
          {info.is_illustrative && (
            <li className="border border-dashed border-gold px-3 py-1 text-xs text-gold">Illustrative demo</li>
          )}
        </ul>
      </div>
    </section>
  );
}
