import Link from "next/link";
import type { CaseSummary } from "@/lib/api";
import { EmptyState } from "@/components/ui/EmptyState";

interface FeaturedCasesProps {
  cases?: CaseSummary[];
  error?: boolean;
}

export function FeaturedCases({ cases, error }: FeaturedCasesProps) {
  if (error || !cases) {
    return (
      <section className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="eyebrow">Judicial Library</p>
            <h2 className="font-serif text-2xl sm:text-3xl text-ivory">Featured Verdicts</h2>
          </div>
        </div>
        <EmptyState
          eyebrow="Data Offline"
          title="Verdicts currently unreachable"
          description="Could not connect to the Hetu verification server. Start the backend API to review indexed judgments."
          actionHref="/methodology"
          actionLabel="Read Platform Methodology"
        />
      </section>
    );
  }

  if (cases.length === 0) {
    return (
      <section className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="eyebrow">Judicial Library</p>
            <h2 className="font-serif text-2xl sm:text-3xl text-ivory">Featured Verdicts</h2>
          </div>
        </div>
        <EmptyState
          eyebrow="Publication Queue"
          title="No published cases yet"
          description="Cases appear here once the court judgment and news coverage have been verified and reviewed by an administrator."
          actionHref="/methodology"
          actionLabel="Learn How Cases Are Verified"
        />
      </section>
    );
  }

  // Display up to 2 featured cases
  const displayCases = cases.slice(0, 2);

  return (
    <section className="flex flex-col gap-6" aria-label="Featured Verdicts">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2 border-b border-gold-line/40 pb-4">
        <div>
          <p className="eyebrow">Judicial Library</p>
          <h2 className="font-serif text-2xl sm:text-3xl text-ivory">Featured Verdicts</h2>
        </div>
        <Link
          href="/verdicts"
          className="text-xs font-semibold text-gold hover:text-ivory transition-colors"
        >
          View all {cases.length} verdicts →
        </Link>
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        {displayCases.map((c) => (
          <article
            key={c.slug}
            className="card flex flex-col justify-between gap-5 p-6 border-gold-line hover:border-gold hover:bg-gold-soft/10 transition-all group"
          >
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between gap-3">
                <span className="eyebrow text-ivory-muted text-[10px]">
                  {c.category}
                  {c.is_illustrative && (
                    <span className="text-gold ml-2">· Illustrative Demo</span>
                  )}
                </span>
                {c.gap_score !== null && (
                  <div className="flex items-baseline gap-1 rounded bg-gold-soft px-2.5 py-1 border border-gold-line">
                    <span className="text-base font-bold text-gold">{Math.round(c.gap_score)}</span>
                    <span className="text-[9px] uppercase tracking-wider text-ivory-faint">PGI</span>
                  </div>
                )}
              </div>

              <h3 className="font-serif text-xl sm:text-2xl text-ivory group-hover:text-gold transition-colors">
                {c.title}
              </h3>

              {c.summary && (
                <p className="text-xs sm:text-sm text-ivory-muted leading-relaxed line-clamp-3">
                  {c.summary}
                </p>
              )}
            </div>

            <div className="border-t border-gold-line/40 pt-4 flex items-center justify-between text-xs">
              <span className="text-ivory-faint">Decided Judgment</span>
              <Link
                href={`/verdicts/${c.slug}`}
                className="font-semibold text-gold group-hover:text-ivory transition-colors inline-flex items-center gap-1"
              >
                <span>Read Analysis</span>
                <span>→</span>
              </Link>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
