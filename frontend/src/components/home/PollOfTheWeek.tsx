import Link from "next/link";
import type { CaseSummary, PollView } from "@/lib/api";

interface PollOfTheWeekProps {
  featuredCase?: CaseSummary;
  poll?: PollView;
}

export function PollOfTheWeek({ featuredCase, poll }: PollOfTheWeekProps) {
  if (!featuredCase) {
    return (
      <section className="card p-6 sm:p-8 bg-surface border-gold-line flex flex-col gap-5">
        <div className="flex items-center justify-between border-b border-gold-line/40 pb-3">
          <div className="flex items-center gap-2">
            <span className="eyebrow text-gold text-[10px]">Democratic Ballot</span>
            <span className="text-xs text-ivory-faint">· Poll of the Week</span>
          </div>
          <span className="text-xs text-ivory-faint font-mono">Status: Awaiting Next Verdict</span>
        </div>

        <div className="flex flex-col gap-2">
          <h3 className="font-serif text-xl sm:text-2xl text-ivory">
            Weekly Public Ballot
          </h3>
          <p className="text-sm text-ivory-muted leading-relaxed">
            Every week, Hetu puts one newly published judicial verdict to the public vote in Jan Mat.
            Participants evaluate judicial reasoning and evidence, never individual accused persons.
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-gold-line/40">
          <p className="text-xs text-ivory-faint">
            We do not open polls or discussion on pending trials.
          </p>
          <Link
            href="/jan-mat"
            className="rounded-md border border-gold-line bg-gold-soft px-4 py-2 text-xs font-semibold text-gold hover:border-gold hover:text-ivory transition-colors"
          >
            Explore Jan Mat Ballots →
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className="card p-6 sm:p-8 bg-surface border-gold-line flex flex-col gap-6" aria-label="Poll of the Week">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gold-line/40 pb-4">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-gold animate-pulse" />
          <span className="eyebrow text-gold text-[10px]">Poll of the Week</span>
        </div>
        <span className="text-xs text-ivory-faint">Decided Verdict Ballot</span>
      </div>

      <div className="flex flex-col gap-3">
        <p className="text-xs text-ivory-muted">Case Under Deliberation:</p>
        <h3 className="font-serif text-2xl text-ivory">
          {poll?.case_title || featuredCase.title}
        </h3>
        <p className="text-sm text-ivory-muted leading-relaxed">
          {poll?.question || "Do you agree with the court's evidentiary findings and sentencing reasoning in this judgment?"}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="rounded border border-gold-line/60 bg-gold-soft/30 p-3 text-center">
          <span className="block text-xs uppercase tracking-wider text-ivory-faint">Option A</span>
          <span className="text-sm font-semibold text-ivory mt-0.5 block">Agree</span>
        </div>
        <div className="rounded border border-gold-line/60 bg-gold-soft/30 p-3 text-center">
          <span className="block text-xs uppercase tracking-wider text-ivory-faint">Option B</span>
          <span className="text-sm font-semibold text-ivory mt-0.5 block">Partly Agree</span>
        </div>
        <div className="rounded border border-gold-line/60 bg-gold-soft/30 p-3 text-center">
          <span className="block text-xs uppercase tracking-wider text-ivory-faint">Option C</span>
          <span className="text-sm font-semibold text-ivory mt-0.5 block">Disagree</span>
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-gold-line/40 text-xs">
        <span className="text-ivory-faint">
          Non-representative engagement. Cryptographically hashed voter tokens.
        </span>
        <Link
          href={poll ? `/jan-mat/${poll.id}` : `/verdicts/${featuredCase.slug}#public`}
          className="rounded-md bg-gold px-4 py-2 font-semibold text-ink hover:bg-bronze transition-colors"
        >
          Cast Your Vote in Jan Mat →
        </Link>
      </div>
    </section>
  );
}
