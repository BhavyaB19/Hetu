import Link from "next/link";

import { JaaliScreen } from "@/components/home/JaaliScreen";
import { ScrollSequence } from "@/components/motion/ScrollSequence";
import type { components } from "@/lib/api/schema";
import type { SequenceManifest } from "@/lib/sequence";

type HomeCounters = components["schemas"]["HomeCounters"];

/** Fades the hero's text out over the first fifth of the scroll so the reveal has the stage. */
const FADE_OUT = { opacity: "calc(1 - var(--seq) * 5)", transform: "translateY(calc(var(--seq) * -48px))" };

function Intro({ pollHref }: { pollHref: string }) {
  return (
    <div
      className="absolute inset-x-4 bottom-4 border border-gold-line bg-ink p-6 sm:inset-x-auto sm:bottom-auto sm:left-8 sm:top-16 sm:w-[28rem] sm:p-9 lg:left-12"
      style={FADE_OUT}
    >
      <p className="eyebrow flex items-center gap-3">
        <span lang="hi" className="font-deva text-base normal-case tracking-normal">
          हेतु
        </span>
        cause, reason
      </p>
      <h1 className="mt-4 font-serif text-4xl leading-[1.04] text-ivory sm:mt-5 sm:text-6xl">
        One verdict. <em className="text-gold">Three</em> stories.
      </h1>
      <p className="mt-4 text-[0.95rem] leading-relaxed text-ivory-muted sm:mt-5 sm:text-base">
        The court&apos;s judgment, the media&apos;s coverage and the public&apos;s reaction to the same Indian criminal
        case, set side by side and measured against the record.
      </p>
      <div className="mt-6 flex flex-wrap gap-3 sm:mt-7">
        <Link href="/verdicts" className="btn-seal">
          Read a verdict
        </Link>
        <Link href={pollHref} className="btn-plain bg-ink">
          Vote in Jan Mat
        </Link>
      </div>
    </div>
  );
}

function Tally({ counters }: { counters: HomeCounters }) {
  const rows = [
    { n: counters.total_cases.toLocaleString("en-IN"), label: "Published verdicts" },
    { n: counters.total_votes.toLocaleString("en-IN"), label: "Jan Mat votes" },
    { n: counters.avg_perception_gap?.toFixed(1) ?? "—", label: "Average perception gap" },
  ];
  return (
    <dl className="absolute right-8 top-16 hidden w-72 border border-gold-line bg-ink lg:right-12 lg:block" style={FADE_OUT}>
      <div className="bg-surface px-5 py-3 text-[11px] uppercase tracking-[0.22em] text-ivory-faint">On the record</div>
      {rows.map((r) => (
        <div key={r.label} className="flex items-center justify-between gap-4 border-t border-gold-line px-5 py-4">
          <dt className="order-2 text-right text-[11px] uppercase tracking-[0.16em] text-ivory-muted">{r.label}</dt>
          <dd className="order-1 font-serif text-3xl leading-none text-ivory">{r.n}</dd>
        </div>
      ))}
    </dl>
  );
}

function ScrollCue() {
  return (
    <p
      className="flex flex-col items-center gap-2 border border-gold-line bg-ink px-4 py-2 text-[11px] uppercase tracking-[0.26em] text-ivory-muted"
      style={{ opacity: "calc(1 - var(--seq) * 8)" }}
    >
      Scroll to open the screen
    </p>
  );
}

type Props = {
  manifest: SequenceManifest | null;
  blink?: { mp4: string; webm?: string };
  counters?: HomeCounters;
  pollHref: string;
};

/**
 * Lady Justice behind the carved screen. Scrolling turns her, the screen opens and the
 * blindfold falls; scrolling back reverses it. Without the footage the screen stands closed
 * over a dark arch, and every word and link is still there.
 */
export function HomeHero({ manifest, blink, counters, pollHref }: Props) {
  const layers = (
    <>
      <JaaliScreen />
      <Intro pollHref={pollHref} />
      {counters && <Tally counters={counters} />}
    </>
  );

  if (!manifest) {
    return (
      <section aria-label="Hetu" className="relative h-[calc(100svh-5rem)] min-h-[36rem] overflow-hidden bg-press" style={{ ["--seq" as string]: 0 }}>
        {layers}
      </section>
    );
  }

  return (
    <ScrollSequence
      manifest={manifest}
      label="Lady Justice turns behind a carved screen; the screen opens and her blindfold falls away"
      runwayVh={320}
      idleVideo={blink}
      steps={[{ at: 0.9, text: "Justice is blind. The public is not." }]}
      stage={layers}
    >
      <ScrollCue />
    </ScrollSequence>
  );
}
