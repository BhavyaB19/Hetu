import Link from "next/link";

interface StoryCard {
  step: string;
  title: string;
  subtitle: string;
  description: string;
  highlights: string[];
  linkHref: string;
  linkLabel: string;
}

const STORIES: StoryCard[] = [
  {
    step: "01",
    title: "The Court's Story",
    subtitle: "Ground Truth in the Record",
    description:
      "What the judgment actually establishes: timeline, motive, evidentiary weight, forensic findings, and legal reasoning.",
    highlights: ["Verbatim quote anchors", "Judicial findings of fact", "Reasoning under statutory law"],
    linkHref: "/verdicts",
    linkLabel: "Browse Judgments →",
  },
  {
    step: "02",
    title: "The Media's Story",
    subtitle: "The Narrative in the Headlines",
    description:
      "How newsrooms framed the proceeding: which claims aligned with the verdict, which were uncorroborated, and what was omitted.",
    highlights: ["Claim verification audits", "Framing tag analysis", "Disproved claim alerts"],
    linkHref: "/verdicts",
    linkLabel: "See Media vs Court →",
  },
  {
    step: "03",
    title: "The Public's Story",
    subtitle: "Democratic Deliberation",
    description:
      "How citizens perceive the outcome: structured Jan Mat polling, thematic analysis, and reasons for agreement or disagreement.",
    highlights: ["Strictly decided cases", "No polls on pending trials", "Anonymized community voice"],
    linkHref: "/jan-mat",
    linkLabel: "Vote in Jan Mat →",
  },
];

export function ThreeStorySection() {
  return (
    <section className="flex flex-col gap-8 py-4" aria-label="The Three Stories">
      <div className="flex flex-col gap-2 text-center max-w-2xl mx-auto">
        <p className="eyebrow">The Tripartite Framework</p>
        <h2 className="font-serif text-3xl sm:text-4xl text-ivory">Three Stories. One Connected Verdict.</h2>
        <p className="text-sm text-ivory-muted leading-relaxed">
          Every criminal proceeding creates three distinct narratives. Hetu aligns them side by side
          to reveal where legal fact and public narrative diverge.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {STORIES.map((story) => (
          <article
            key={story.title}
            className="card flex flex-col justify-between p-6 sm:p-7 border-gold-line bg-surface hover:border-gold/80 transition-all hover:bg-gold-soft/10 group"
          >
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-gold px-2.5 py-0.5 rounded border border-gold-line bg-gold-soft">
                  Story {story.step}
                </span>
                <span className="text-[11px] text-ivory-faint tracking-wider uppercase font-sans">
                  {story.subtitle}
                </span>
              </div>

              <div>
                <h3 className="font-serif text-2xl text-ivory group-hover:text-gold transition-colors">
                  {story.title}
                </h3>
                <p className="text-sm text-ivory-muted mt-2 leading-relaxed">
                  {story.description}
                </p>
              </div>

              <ul className="flex flex-col gap-1.5 pt-2 border-t border-gold-line/40 text-xs text-ivory">
                {story.highlights.map((item) => (
                  <li key={item} className="flex items-center gap-2">
                    <span className="h-1 w-1 rounded-full bg-gold shrink-0" />
                    <span className="text-ivory-muted">{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="pt-6 mt-4 border-t border-gold-line/30">
              <Link
                href={story.linkHref}
                className="text-xs font-semibold text-gold group-hover:text-ivory transition-colors inline-flex items-center gap-1.5"
              >
                <span>{story.linkLabel}</span>
              </Link>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
