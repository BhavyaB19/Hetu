import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Live Docket — Ongoing Proceedings | Hetu",
  description:
    "Tracking active criminal proceedings across Indian courts with neutral procedural milestones. We do not open polls or discussion on pending trials.",
};

const DOCKET_STAGES = [
  {
    stage: "Investigation / Charge Sheet",
    description: "FIR filings, police reports, forensic submissions, and cognizance orders.",
  },
  {
    stage: "Pre-Trial & Charges Framed",
    description: "Discharge applications, framing of formal charges under the BNS / IPC.",
  },
  {
    stage: "Prosecution & Defence Evidence",
    description: "Witness examination (chief & cross), documentary exhibits, Section 313 statements.",
  },
  {
    stage: "Final Arguments",
    description: "Oral submissions, precedents cited, and legal points urged before the bench.",
  },
  {
    stage: "Judgment Reserved",
    description: "Hearing concluded; bench reserves verdict. No further arguments entertained.",
  },
  {
    stage: "Verdict Pronounced (Moves to Verdicts)",
    description: "Final judgment signed and released. Transferred to Hetu Verdicts library for Perception Gap indexing.",
  },
];

export default function LiveDocketPage() {
  return (
    <div className="flex flex-col gap-12 max-w-4xl mx-auto py-6">
      {/* Header */}
      <header className="flex flex-col gap-3 border-b border-gold-line pb-6">
        <p className="eyebrow">Active Proceedings Monitor</p>
        <h1 className="font-serif text-3xl sm:text-5xl text-ivory">Live Docket</h1>
        <p className="text-base text-ivory-muted leading-relaxed max-w-2xl">
          A neutral, factual window into active criminal proceedings across India&apos;s High Courts
          and the Supreme Court. Tracking hearing schedules, stages, and procedural orders without sensationalism.
        </p>
      </header>

      {/* Honest Status Callout */}
      <section className="card p-6 sm:p-8 bg-surface border-gold-line flex flex-col gap-5">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gold-line/40 pb-4">
          <div className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-ivory-muted" />
            <span className="text-xs font-semibold uppercase tracking-wider text-ivory-muted">
              Roadmap Feature
            </span>
          </div>
          <span className="text-xs text-ivory-faint font-mono">Status: Not Yet Live</span>
        </div>

        <div className="flex flex-col gap-3">
          <h2 className="font-serif text-2xl text-ivory">On the roadmap — not yet live</h2>
          <p className="text-sm text-ivory-muted leading-relaxed">
            The Live Docket is on our product roadmap and has not yet launched.
            Rather than populating this section with placeholder cases or synthetic data, this surface
            will open only once live court causelist tracking is ready for public release.
          </p>
          <p className="text-sm text-ivory-muted leading-relaxed">
            When launched, ongoing proceedings tracked here will cite official court causelists, dates of hearing,
            and verbatim procedural orders from court records.
          </p>
        </div>

        <div className="flex flex-wrap gap-3 pt-2">
          <Link
            href="/verdicts"
            className="rounded-md bg-gold px-5 py-2.5 text-sm font-semibold text-ink hover:bg-bronze transition-colors"
          >
            Explore Decided Cases in Verdicts →
          </Link>
          <Link
            href="/methodology"
            className="rounded-md border border-gold-line bg-gold-soft px-5 py-2.5 text-sm font-medium text-gold hover:border-gold hover:text-ivory transition-colors"
          >
            Read Our Methodology
          </Link>
        </div>
      </section>

      {/* Ethical Guard: Pending Trials Policy */}
      <section className="card p-6 sm:p-8 border-gold-line/60 bg-gold-soft/20 flex flex-col gap-4">
        <div className="flex items-center gap-2">
          <svg className="h-5 w-5 text-gold shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <h3 className="font-serif text-xl text-ivory">Policy on Pending Trials</h3>
        </div>
        <div className="space-y-3 text-sm text-ivory-muted leading-relaxed">
          <p className="text-ivory font-medium">
            We do not open polls or discussion on pending trials. Trials belong in courtrooms, not in courtrooms of public opinion.
          </p>
          <ul className="list-disc pl-5 space-y-2 text-xs sm:text-sm text-ivory">
            <li>
              <strong className="text-gold">No Guilt Polls:</strong> We never conduct opinion polls on pending or ongoing trials.
            </li>
            <li>
              <strong className="text-gold">No Outcome Speculation:</strong> We will never predict verdicts, bail grants, or sentences.
            </li>
            <li>
              <strong className="text-gold">No Pre-Trial Commentary:</strong> Public voting and comment forums are locked until a final, appealable judgment is pronounced and officially published.
            </li>
            <li>
              <strong className="text-gold">Neutral Hearing Logs:</strong> Tracking is strictly confined to date, presiding bench, procedural stage, and verbatim excerpts from public judicial orders.
            </li>
          </ul>
        </div>
      </section>

      {/* Procedural Pipeline */}
      <section className="flex flex-col gap-5">
        <div className="flex flex-col gap-1">
          <p className="eyebrow">Procedural Framework</p>
          <h2 className="font-serif text-2xl text-ivory">How Proceedings Will Be Tracked</h2>
          <p className="text-sm text-ivory-muted">
            Cases on the Live Docket will transition through official procedural milestones:
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {DOCKET_STAGES.map((st, i) => (
            <div key={st.stage} className="card p-5 flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="eyebrow text-gold">Stage 0{i + 1}</span>
              </div>
              <h3 className="font-serif text-lg text-ivory">{st.stage}</h3>
              <p className="text-xs text-ivory-muted leading-relaxed">{st.description}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
