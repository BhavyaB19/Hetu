import Link from "next/link";

import type { PollView } from "@/lib/api";

const CHOICES = ["Agree", "Partly", "Disagree"];

/** The public's opening, set as a reversed ink block: the promise, the rules, and this week's ballot. */
export function JanMatPanel({ poll }: { poll?: PollView }) {
  const href = poll ? `/jan-mat/${poll.id}` : "/jan-mat";
  return (
    <section aria-labelledby="janmat" className="reverse px-4 py-20 sm:px-8 sm:py-28 lg:px-12">
      <div className="mx-auto grid max-w-[90rem] items-center gap-14 lg:grid-cols-[1fr_32rem] lg:gap-20">
        <div>
          <p className="eyebrow flex items-center gap-2">
            Jan Mat ·{" "}
            <span lang="hi" className="font-deva normal-case tracking-normal">
              जन मत
            </span>
          </p>
          <h2 id="janmat" className="mt-4 font-serif text-4xl leading-[1.08] sm:text-6xl">
            Justice is blind.
            <br />
            <em className="text-gold">The public is not.</em>
          </h2>
          <ul className="mt-8 flex flex-col gap-3 text-[0.95rem] text-ivory-muted">
            {[
              "Polls open only after a verdict is published.",
              "Your vote is anonymous. We never store your IP address.",
              "Comments are moderated. Criticise the reasoning, not the people.",
            ].map((r) => (
              <li key={r} className="flex items-start gap-3">
                <span className="lozenge mt-2" aria-hidden />
                {r}
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-t-full border border-gold bg-surface px-6 pb-10 pt-24 sm:px-12 sm:pt-28">
          {poll ? (
            <>
              <p className="text-center text-xs uppercase tracking-[0.2em] text-ivory-faint">{poll.case_title ?? "Ballot of the week"}</p>
              <p className="mt-3 text-center font-serif text-2xl leading-snug sm:text-3xl">{poll.question}</p>
              <div className="mt-8 grid grid-cols-3 gap-2.5">
                {CHOICES.map((c) => (
                  <Link
                    key={c}
                    href={href}
                    className="flex h-20 flex-col items-center justify-center gap-2 border border-gold-line text-sm transition-colors hover:border-gold hover:bg-gold-soft"
                  >
                    <span className="h-3 w-3 rotate-45 border-[1.5px] border-gold" aria-hidden />
                    {c}
                  </Link>
                ))}
              </div>
              <p className="mt-5 text-center text-xs uppercase tracking-[0.14em] text-ivory-faint">
                {poll.total_votes.toLocaleString("en-IN")} votes · Not a representative sample
              </p>
            </>
          ) : (
            <>
              <p className="text-center font-serif text-2xl leading-snug">No ballot is open this week.</p>
              <p className="mt-3 text-center text-sm text-ivory-muted">Ballots open once a decided verdict is published.</p>
              <div className="mt-8 flex justify-center">
                <Link href="/jan-mat" className="btn-seal">
                  See past ballots
                </Link>
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
