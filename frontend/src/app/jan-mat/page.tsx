import Link from "next/link";
import type { Metadata } from "next";

import { EmptyState } from "@/components/ui/EmptyState";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Jan Mat — Public Opinion on Decided Verdicts | Hetu",
  description:
    "Participate in public deliberation on published Indian criminal judgments. Structured ballots, reasons, and community commentary on decided cases.",
};

export default async function JanMatPage() {
  const { data: cases } = await api
    .GET("/cases")
    .catch(() => ({ data: undefined }));

  return (
    <div className="flex flex-col gap-10 py-6">
      <header className="flex flex-col gap-3 border-b border-gold-line pb-6">
        <p className="eyebrow">Democratic Deliberation</p>
        <h1 className="font-serif text-3xl sm:text-5xl text-ivory">Jan Mat (जन मत)</h1>
        <p className="text-base text-ivory-muted leading-relaxed max-w-2xl">
          Public polling and discourse on signed, published judicial verdicts.
          Voice your perspective on judicial reasoning, proportionality, and evidence without personal abuse.
        </p>
      </header>

      {/* Disclaimers & Ethics */}
      <section className="card p-5 sm:p-6 bg-gold-soft/10 border-gold-line flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex flex-col gap-1 text-xs text-ivory-muted leading-relaxed max-w-xl">
          <p>
            <strong className="text-gold">Non-Representative Sample:</strong> Jan Mat polls reflect digital participation, not a scientific cross-section of India.
          </p>
          <p>
            <strong className="text-gold">Pending Trials Policy:</strong> We do not open polls or discussion on pending trials.
          </p>
        </div>
        <Link
          href="/methodology"
          className="shrink-0 text-xs font-semibold text-gold hover:text-ivory transition-colors"
        >
          Read Policy →
        </Link>
      </section>

      {/* Ballots Listing */}
      <section className="flex flex-col gap-5">
        <div className="flex items-center justify-between">
          <h2 className="font-serif text-2xl text-ivory">Open Verdict Ballots</h2>
          <span className="text-xs text-ivory-faint">Decided Cases Only</span>
        </div>

        {!cases || cases.length === 0 ? (
          <EmptyState
            eyebrow="Ballot Queue Empty"
            title="No active ballots at this moment"
            description="Polls open automatically upon publication of reviewed criminal judgments. Check back shortly as new verdicts are published."
            actionHref="/verdicts"
            actionLabel="Browse Decided Cases"
          />
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {cases.map((c) => (
              <div
                key={c.slug}
                className="card flex flex-col justify-between gap-5 p-6 border-gold-line"
              >
                <div className="flex flex-col gap-2.5">
                  <div className="flex items-center justify-between">
                    <span className="eyebrow text-gold text-[10px]">Open Ballot</span>
                    <span className="text-xs text-ivory-faint">3 Options: Agree · Partly · Disagree</span>
                  </div>
                  <h3 className="font-serif text-xl text-ivory">{c.title}</h3>
                  <p className="text-xs text-ivory-muted leading-relaxed">
                    {c.summary || "Case record published by the registry."}
                  </p>
                </div>

                <div className="border-t border-gold-line/40 pt-4 flex items-center justify-between">
                  <div className="text-xs text-ivory-faint">
                    <span>Perception Gap: </span>
                    <span className="text-gold font-medium">
                      {c.gap_score !== null ? `${Math.round(c.gap_score)}/100` : "Pending"}
                    </span>
                  </div>
                  <Link
                    href={`/verdicts/${c.slug}#public`}
                    className="rounded-md bg-gold px-3.5 py-1.5 text-xs font-semibold text-ink hover:bg-bronze transition-colors"
                  >
                    View &amp; Vote →
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
