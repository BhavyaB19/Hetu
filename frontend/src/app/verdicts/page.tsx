import Link from "next/link";
import type { Metadata } from "next";

import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Verdicts Library — Decided Criminal Cases | Hetu",
  description:
    "Explore decided Indian criminal judgments analyzed side-by-side with news reporting and public sentiment through the Perception Gap Index.",
};

export default async function VerdictsPage() {
  const { data: cases, error } = await api
    .GET("/cases")
    .catch(() => ({ data: undefined, error: true }));

  return (
    <div className="flex flex-col gap-10 py-6">
      <header className="flex flex-col gap-3 border-b border-gold-line pb-6">
        <p className="eyebrow">Judicial Library</p>
        <h1 className="font-serif text-3xl sm:text-5xl text-ivory">Verdicts</h1>
        <p className="text-base text-ivory-muted leading-relaxed max-w-2xl">
          Completed criminal judgments from the Supreme Court and High Courts of India,
          measured against press coverage and public perception via the Perception Gap Index.
        </p>
      </header>

      {error || !cases ? (
        <ErrorState
          eyebrow="API Offline"
          title="Unable to connect to the verdict repository"
          message="Could not retrieve the published cases list from the Hetu API. Ensure the backend server is active."
        />
      ) : cases.length === 0 ? (
        <EmptyState
          eyebrow="No Verdicts Published"
          title="No cases have been published yet"
          description="Cases are published after full judicial extraction and human-in-the-loop review. Check back shortly or seed the demonstrator database."
          actionHref="/"
          actionLabel="Return to Home"
        />
      ) : (
        <div className="flex flex-col gap-6">
          <div className="flex items-center justify-between text-xs text-ivory-muted">
            <span>Showing {cases.length} published {cases.length === 1 ? "verdict" : "verdicts"}</span>
            <span className="text-gold">Sorted by latest publication</span>
          </div>

          <ul className="grid gap-4 md:grid-cols-2">
            {cases.map((c) => (
              <li key={c.slug}>
                <Link
                  href={`/verdicts/${c.slug}`}
                  className="card flex h-full flex-col justify-between gap-4 p-6 transition-all hover:border-gold hover:bg-gold-soft/10"
                >
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center justify-between gap-2">
                      <p className="eyebrow text-[11px] text-ivory-muted">
                        {c.category}
                        {c.is_illustrative && (
                          <span className="ml-2 text-gold">· Illustrative demo</span>
                        )}
                      </p>
                      {c.gap_score !== null && (
                        <div className="inline-flex items-baseline gap-1 rounded bg-gold-soft px-2 py-0.5 border border-gold-line">
                          <span className="text-sm font-bold text-gold">{Math.round(c.gap_score)}</span>
                          <span className="text-[9px] uppercase tracking-wider text-ivory-faint">PGI</span>
                        </div>
                      )}
                    </div>
                    <h2 className="font-serif text-xl sm:text-2xl text-ivory hover:text-gold transition-colors">
                      {c.title}
                    </h2>
                    {c.summary && (
                      <p className="text-sm leading-relaxed text-ivory-muted line-clamp-3">
                        {c.summary}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center justify-between border-t border-gold-line/40 pt-3 text-xs text-ivory-muted">
                    <span>View 3-Story Breakdown</span>
                    <span className="text-gold font-semibold">Read Analysis →</span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
