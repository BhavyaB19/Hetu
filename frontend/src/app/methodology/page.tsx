import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Methodology & Ethical Standards | Hetu",
  description:
    "How Hetu measures narrative divergence with the Perception Gap Index, ethical data collection, strict anonymization, and pending trial policies.",
};

export default function MethodologyPage() {
  return (
    <div className="flex flex-col gap-14 max-w-4xl mx-auto py-6">
      {/* Header */}
      <header className="flex flex-col gap-3 border-b border-gold-line pb-6">
        <p className="eyebrow">Rigour &amp; Transparency</p>
        <h1 className="font-serif text-3xl sm:text-5xl text-ivory">Methodology &amp; Standards</h1>
        <p className="text-base text-ivory-muted leading-relaxed max-w-2xl">
          Hetu is an open research platform investigating the divergence between legal fact,
          journalistic framing, and public sentiment in Indian criminal jurisprudence.
        </p>
      </header>

      {/* 1. Perception Gap Index - exactly matching backend/app/services/scoring.py */}
      <section className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <p className="eyebrow">Metric Definition</p>
          <h2 className="font-serif text-2xl sm:text-3xl text-ivory">The Perception Gap Index (PGI)</h2>
          <p className="text-sm text-ivory-muted leading-relaxed">
            The Perception Gap Index is a normalized scalar score ranging from <strong>0 (complete alignment)</strong> to <strong>100 (extreme divergence)</strong>. It quantifies how significantly media reporting and public perception deviate from the factual findings and legal reasoning recorded in a signed judicial verdict.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="card p-5 flex flex-col gap-2">
            <span className="eyebrow text-gold">Factual divergence (30% Weight)</span>
            <h3 className="font-serif text-lg text-ivory">Factual Divergence</h3>
            <p className="text-xs text-ivory-muted leading-relaxed">
              Claims extracted from media coverage are audited against the signed judgment. A claim is scored based on whether it is contradicted by the judgment (full penalty) or absent from it (absent claims count half).
            </p>
          </div>

          <div className="card p-5 flex flex-col gap-2">
            <span className="eyebrow text-gold">Framing gap (25% Weight)</span>
            <h3 className="font-serif text-lg text-ivory">Framing Gap</h3>
            <p className="text-xs text-ivory-muted leading-relaxed">
              The court reasons procedurally and neutrally. The framing gap measures the share of articles that adopt a non-procedural frame alongside their average emotional intensity on a 0 to 1 scale.
            </p>
          </div>

          <div className="card p-5 flex flex-col gap-2">
            <span className="eyebrow text-gold">Public sentiment gap (25% Weight)</span>
            <h3 className="font-serif text-lg text-ivory">Public Sentiment Gap</h3>
            <p className="text-xs text-ivory-muted leading-relaxed">
              Measures how far public reactions sit from the court&apos;s final outcome (conviction or acquittal). The gap tracks reactions taking the opposing side, while neutral and media-bias reactions count half.
            </p>
          </div>

          <div className="card p-5 flex flex-col gap-2">
            <span className="eyebrow text-gold">Timeline distortion (20% Weight)</span>
            <h3 className="font-serif text-lg text-ivory">Timeline Distortion</h3>
            <p className="text-xs text-ivory-muted leading-relaxed">
              Average gap between how much the court and the media emphasise each event across the case timeline, comparing court weight against the share of media articles that mention the event.
            </p>
          </div>
        </div>
      </section>

      {/* 2. Verbatim Quote Anchoring */}
      <section className="card p-6 sm:p-8 bg-surface border-gold-line flex flex-col gap-4">
        <p className="eyebrow text-gold">Verifiable Evidence</p>
        <h2 className="font-serif text-2xl text-ivory">Verbatim Quote Anchoring</h2>
        <p className="text-sm text-ivory-muted leading-relaxed">
          In Hetu, no finding, timeline event, or media claim exists without a direct, verifiable citation.
          Every court finding links to an unedited quote span directly in the official judgment text. If an algorithmic claim cannot be matched against a verbatim quote in the primary source document, it is dropped from the dataset.
        </p>
      </section>

      {/* 3. Sub Judice & Pending Trials Policy */}
      <section className="card p-6 sm:p-8 border-gold-line/70 bg-gold-soft/10 flex flex-col gap-4">
        <p className="eyebrow text-gold">Legal Ethics</p>
        <h2 className="font-serif text-2xl text-ivory">Policy on Pending Trials &amp; Non-Prediction</h2>
        <div className="space-y-3 text-sm text-ivory-muted leading-relaxed">
          <p className="text-ivory font-medium">
            We do not open polls or discussion on pending trials.
          </p>
          <ul className="list-disc pl-5 space-y-2 text-xs sm:text-sm text-ivory">
            <li>
              <strong>No polls on pending trials:</strong> Opinion polls and public commentary are strictly prohibited while a case is ongoing. Jan Mat ballots open only after a final, signed verdict is published.
            </li>
            <li>
              <strong>Zero outcome prediction:</strong> Hetu will never estimate probabilities of guilt, acquittal, bail grants, or sentence severity. We analyze the record of the past, not speculate on the future.
            </li>
            <li>
              <strong>Criticism of reasoning, not people:</strong> Public commentary on decided cases is moderated to maintain discussion on judicial reasoning and statutory evidence, strictly disallowing personal abuse of judges or judicial officers.
            </li>
          </ul>
        </div>
      </section>

      {/* 4. Privacy & Anonymization */}
      <section className="flex flex-col gap-4">
        <p className="eyebrow">Privacy Architecture</p>
        <h2 className="font-serif text-2xl text-ivory">Anonymization Protocol</h2>
        <p className="text-sm text-ivory-muted leading-relaxed">
          Prior to ingestion into the database, our pipelines pass all records through an anonymization layer:
        </p>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="card p-5">
            <h3 className="font-serif text-base text-ivory mb-2">Private Individuals Masked</h3>
            <p className="text-xs text-ivory-muted leading-relaxed">
              Accused persons, victims, witnesses, family members, and minors are systematically substituted with standardized placeholders (e.g., <code className="text-gold">[Accused-1]</code>, <code className="text-gold">[Witness-A]</code>) to safeguard individual privacy and prevent harassment.
            </p>
          </div>
          <div className="card p-5">
            <h3 className="font-serif text-base text-ivory mb-2">Public Officials Identified</h3>
            <p className="text-xs text-ivory-muted leading-relaxed">
              Judges, designated prosecutors, and government officials acting in their official, public capacity are preserved in accordance with open-justice standards.
            </p>
          </div>
        </div>
      </section>

      {/* 5. Sources & Limits */}
      <section className="flex flex-col gap-4">
        <p className="eyebrow">Transparency</p>
        <h2 className="font-serif text-2xl text-ivory">Data Sources &amp; Limitations</h2>
        <div className="space-y-3 text-sm text-ivory-muted leading-relaxed">
          <p>
            <strong>Sources:</strong> Judgments are retrieved from official Supreme Court of India registries and High Court portals. Media reports are sampled from accredited, publicly accessible news publishers with full respect for <code className="text-gold">robots.txt</code>. We do not bypass logins, paywalls, or CAPTCHAs.
          </p>
          <p>
            <strong>Sample Representation:</strong> Votes cast on Jan Mat represent an engaged digital audience. They do <em>not</em> represent a scientifically weighted or demographically representative sample of India&apos;s overall population. All public polling charts clearly carry this notice.
          </p>
        </div>
      </section>

      {/* 6. Corrections & Takedowns */}
      <section className="card p-6 sm:p-8 bg-surface border-gold-line flex flex-col gap-3">
        <p className="eyebrow text-gold">Accountability</p>
        <h2 className="font-serif text-xl sm:text-2xl text-ivory">Corrections &amp; Takedown Requests</h2>
        <p className="text-sm text-ivory-muted leading-relaxed">
          If you identify an inaccurate quote anchor, an anonymization failure, or an erroneous citation, please submit a report. All flagged entries are reviewed by our moderation and editorial desk.
        </p>
        <div className="pt-2">
          <Link
            href="/verdicts"
            className="inline-flex items-center gap-2 text-sm text-gold hover:text-ivory transition-colors"
          >
            ← Explore Published Verdicts
          </Link>
        </div>
      </section>
    </div>
  );
}
