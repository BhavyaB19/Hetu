import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";

import { CourtVsMedia } from "@/components/CourtVsMedia";
import { GapIndex } from "@/components/GapIndex";
import { Insights } from "@/components/Insights";
import { MediaCoverage } from "@/components/MediaCoverage";
import { PublicReaction } from "@/components/PublicReaction";
import { Section } from "@/components/Section";
import { Timeline } from "@/components/Timeline";
import { ErrorState } from "@/components/ui/ErrorState";
import { api } from "@/lib/api";
import { date } from "@/lib/format";

export const dynamic = "force-dynamic";

const NAV = [
  ["timeline", "Timeline"],
  ["court-vs-media", "Court vs Media"],
  ["public", "Public Reaction"],
  ["coverage", "Coverage"],
  ["sources", "Sources"],
];

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const { data: view } = await api
    .GET("/cases/{slug}", { params: { path: { slug } } })
    .catch(() => ({ data: undefined }));

  if (!view) {
    return {
      title: "Verdict Analysis | Hetu",
    };
  }

  return {
    title: `${view.case.title} — Perception Gap Analysis | Hetu`,
    description: view.case.summary || "Case analysis comparing judgment findings against media coverage and public sentiment.",
  };
}

export default async function VerdictPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const { data: view, response } = await api
    .GET("/cases/{slug}", { params: { path: { slug } } })
    .catch(() => ({ data: undefined, response: undefined }));

  if (response?.status === 404) notFound();
  if (!view) {
    return (
      <ErrorState
        eyebrow="Verdict Lookup"
        title="Unable to load case record"
        message="The Hetu backend could not be reached or returned an error. Please verify the API service status."
      />
    );
  }
  const { case: info } = view;

  return (
    <div className="flex flex-col gap-12">
      <header className="flex flex-col gap-3">
        <Link href="/verdicts" className="text-sm text-ivory-muted hover:text-gold transition-colors">
          ← All verdicts
        </Link>
        <p className="eyebrow">
          {info.category}
          {info.court && ` · ${info.court}`}
        </p>
        <h1 className="font-serif text-3xl text-ivory sm:text-5xl">{info.title}</h1>
        {info.summary && <p className="max-w-3xl text-ivory-muted text-base leading-relaxed">{info.summary}</p>}
        {info.is_illustrative && (
          <p className="w-fit rounded-md border border-gold-line bg-gold-soft px-3 py-1.5 text-xs text-gold">
            Illustrative demo: prototype data, not sourced from a real-world case.
          </p>
        )}

        {/* Action strip with Jan Mat link */}
        <div className="flex flex-wrap items-center justify-between gap-4 mt-2 pt-2 border-t border-gold-line/40">
          <nav className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-ivory-muted">
            {NAV.map(([id, label]) => (
              <a key={id} href={`#${id}`} className="hover:text-gold transition-colors">
                {label}
              </a>
            ))}
          </nav>
          <Link
            href="/jan-mat"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-gold bg-gold-soft border border-gold-line px-3 py-1.5 rounded hover:border-gold hover:text-ivory transition-colors"
          >
            <span>Vote on this verdict in Jan Mat</span>
            <span>→</span>
          </Link>
        </div>
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
            <thead className="text-xs uppercase tracking-widest text-ivory-faint border-b border-gold-line/40">
              <tr>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">Source</th>
                <th className="px-4 py-3 font-medium">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gold-line">
              {view.sources.map((s) => (
                <tr key={s.key} className="hover:bg-gold-soft/20 transition-colors">
                  <td className="px-4 py-2.5 capitalize text-ivory-muted text-xs">{s.source_type}</td>
                  <td className="px-4 py-2.5 text-ivory">
                    {s.url ? (
                      <a href={s.url} target="_blank" rel="noreferrer" className="hover:text-gold transition-colors">
                        {s.source_name} ↗
                      </a>
                    ) : (
                      s.source_name
                    )}
                  </td>
                  <td className="whitespace-nowrap px-4 py-2.5 text-ivory-muted text-xs">{date(s.published_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </div>
  );
}
