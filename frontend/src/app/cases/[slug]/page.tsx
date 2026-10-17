import Link from "next/link";
import { notFound } from "next/navigation";

import { CourtVsMedia } from "@/components/CourtVsMedia";
import { GapIndex } from "@/components/GapIndex";
import { Insights } from "@/components/Insights";
import { MediaCoverage } from "@/components/MediaCoverage";
import { PublicReaction } from "@/components/PublicReaction";
import { Section } from "@/components/Section";
import { Timeline } from "@/components/Timeline";
import { API_URL, api } from "@/lib/api";
import { date } from "@/lib/format";

export const dynamic = "force-dynamic";

const NAV = [
  ["timeline", "Timeline"],
  ["court-vs-media", "Court vs Media"],
  ["public", "Public Reaction"],
  ["coverage", "Coverage"],
  ["sources", "Sources"],
];

export default async function CasePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const { data: view, response } = await api
    .GET("/cases/{slug}", { params: { path: { slug } } })
    .catch(() => ({ data: undefined, response: undefined }));

  if (response?.status === 404) notFound();
  if (!view) {
    return <p className="card p-6 text-sm text-ivory-muted">Can&apos;t reach the Hetu API at {API_URL}.</p>;
  }
  const { case: info } = view;

  return (
    <div className="flex flex-col gap-14">
      <header className="flex flex-col gap-3">
        <Link href="/" className="text-sm text-ivory-muted hover:text-gold">
          ← All cases
        </Link>
        <p className="eyebrow">
          {info.category}
          {info.court && ` · ${info.court}`}
        </p>
        <h1 className="font-serif text-4xl text-ivory sm:text-5xl">{info.title}</h1>
        {info.summary && <p className="max-w-3xl text-ivory-muted">{info.summary}</p>}
        {info.is_illustrative && (
          <p className="w-fit rounded-md border border-gold-line bg-gold-soft px-3 py-2 text-xs text-gold">
            Illustrative demo: prototype data, not sourced from a real-world case.
          </p>
        )}
        <nav className="mt-2 flex flex-wrap gap-x-5 gap-y-2 border-b border-gold-line pb-3 text-sm text-ivory-muted">
          {NAV.map(([id, label]) => (
            <a key={id} href={`#${id}`} className="hover:text-gold">
              {label}
            </a>
          ))}
        </nav>
      </header>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        {view.gap && <GapIndex gap={view.gap} />}
        <Insights view={view} />
      </div>

      {view.timeline.length > 0 && (
        <Section id="timeline" eyebrow="Escalation" title="Case timeline">
          <Timeline events={view.timeline} />
        </Section>
      )}

      {view.judgment && (
        <Section id="court-vs-media" eyebrow="Two narratives" title="Court vs Media">
          <CourtVsMedia judgment={view.judgment} media={view.media} />
        </Section>
      )}

      <Section id="public" eyebrow="The public's story" title="Public reaction">
        <PublicReaction data={view.public} />
      </Section>

      <Section id="coverage" eyebrow="The media's story" title="Coverage">
        <MediaCoverage media={view.media} />
      </Section>

      <Section id="sources" eyebrow="Evidence base" title="Sources">
        <div className="card overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-widest text-ivory-faint">
              <tr>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">Source</th>
                <th className="px-4 py-3 font-medium">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gold-line">
              {view.sources.map((s) => (
                <tr key={s.key}>
                  <td className="px-4 py-2.5 capitalize text-ivory-muted">{s.source_type}</td>
                  <td className="px-4 py-2.5 text-ivory">
                    {s.url ? (
                      <a href={s.url} target="_blank" rel="noreferrer" className="hover:text-gold">
                        {s.source_name} ↗
                      </a>
                    ) : (
                      s.source_name
                    )}
                  </td>
                  <td className="whitespace-nowrap px-4 py-2.5 text-ivory-muted">{date(s.published_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </div>
  );
}
