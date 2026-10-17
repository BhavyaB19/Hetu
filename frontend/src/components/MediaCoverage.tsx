import type { MediaView } from "@/lib/api";
import { FRAMING, VERDICT, date, tone } from "@/lib/format";

/** Each article with its framing, tone and a one-line tally of its checked claims. */
export function MediaCoverage({ media }: { media: MediaView[] }) {
  return (
    <ul className="grid gap-4 md:grid-cols-2">
      {media.map((article) => (
        <li key={article.document} className="card flex flex-col gap-3 p-5">
          <p className="text-xs text-ivory-muted">
            {article.outlet} · {date(article.published_at)}
          </p>
          <h3 className="font-serif text-lg leading-snug text-ivory">
            {article.url ? (
              <a href={article.url} target="_blank" rel="noreferrer" className="hover:text-gold">
                {article.headline}
              </a>
            ) : (
              article.headline
            )}
          </h3>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-full border border-gold-line px-3 py-1 text-ivory">{FRAMING[article.framing]}</span>
            <span className="rounded-full border border-gold-line px-3 py-1 text-ivory-muted">Tone {tone(article.tone)}</span>
          </div>
          <p className="text-sm text-ivory-muted">{article.narratives.join(" · ")}</p>
          <p className="mt-auto flex flex-wrap gap-x-4 text-xs">
            {(Object.keys(VERDICT) as (keyof typeof VERDICT)[]).map((v) => {
              const n = article.claims.filter((c) => c.verdict === v).length;
              return n ? (
                <span key={v} className={VERDICT[v].className}>
                  {VERDICT[v].icon} {n} {VERDICT[v].label.toLowerCase()}
                </span>
              ) : null;
            })}
          </p>
        </li>
      ))}
    </ul>
  );
}
