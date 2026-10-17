import type { CaseView } from "@/lib/api";
import { SENTIMENT, pct } from "@/lib/format";

/** Plain-language takeaways derived from the case data. */
export function insightsFor(view: CaseView): string[] {
  const out: string[] = [];
  const top = view.gap?.components.toSorted((a, b) => b.contribution - a.contribution)[0];
  if (top && top.contribution > 0) {
    out.push(`${top.label} contributes most to the gap (${top.contribution.toFixed(1)} of ${Math.round(view.gap!.score)} points).`);
  }

  const claims = view.media.flatMap((m) => m.claims);
  const contradicted = claims.filter((c) => c.verdict === "contradicted").length;
  if (claims.length) {
    out.push(`${contradicted} of ${claims.length} factual claims in the coverage are contradicted by the judgment.`);
  }

  const skew = view.timeline
    .map((e) => ({ e, diff: e.media_weight - e.court_weight }))
    .toSorted((a, b) => Math.abs(b.diff) - Math.abs(a.diff))[0];
  if (skew && Math.abs(skew.diff) >= 0.2) {
    out.push(
      skew.diff > 0
        ? `Media gave "${skew.e.label}" far more attention (${pct(skew.e.media_weight)} of articles) than the court did.`
        : `"${skew.e.label}" was central for the court but covered by only ${pct(skew.e.media_weight)} of articles.`,
    );
  }

  const lead = view.public.sentiment.toSorted((a, b) => b.share - a.share)[0];
  if (lead && view.public.total) {
    const label = SENTIMENT[lead.key as keyof typeof SENTIMENT].label;
    out.push(`The most common public stance is "${label}", in ${pct(lead.share)} of reactions.`);
  }
  const theme = view.public.themes[0];
  if (theme) out.push(`"${theme.key}" is the most common theme, in ${pct(theme.share)} of reactions.`);
  return out;
}

export function Insights({ view }: { view: CaseView }) {
  const items = insightsFor(view);
  return (
    <div className="card flex flex-col gap-4 p-6">
      <p className="eyebrow">Insights</p>
      <ul className="flex flex-col gap-3">
        {items.map((text) => (
          <li key={text} className="flex gap-3 text-sm leading-relaxed text-ivory">
            <span className="mt-2 h-1 w-3 shrink-0 bg-gold" aria-hidden />
            {text}
          </li>
        ))}
      </ul>
    </div>
  );
}
