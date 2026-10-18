import Link from "next/link";
import { notFound } from "next/navigation";

import { CourtVsMedia } from "@/components/CourtVsMedia";
import { GapIndex } from "@/components/GapIndex";
import { Insights } from "@/components/Insights";
import { MediaCoverage } from "@/components/MediaCoverage";
import { PublicReaction } from "@/components/PublicReaction";
import { Section } from "@/components/Section";
import { Timeline } from "@/components/Timeline";
import { API_URL } from "@/lib/api";
import { date } from "@/lib/format";
import type { CaseView } from "@/lib/api";

export const dynamic = "force-dynamic";

const ADMIN_API_KEY = process.env.ADMIN_API_KEY ?? "hetu-dev-admin-key";

const NAV = [
  ["timeline", "Timeline"],
  ["court-vs-media", "Court vs Media"],
  ["public", "Public Reaction"],
  ["coverage", "Coverage"],
  ["sources", "Sources"],
];

export default async function AdminCasePreviewPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;

  let view: CaseView | undefined;
  try {
    const res = await fetch(`${API_URL}/admin/cases/${encodeURIComponent(slug)}/preview`, {
      headers: {
        "X-Admin-Key": ADMIN_API_KEY,
      },
      cache: "no-store",
    });
    if (res.status === 404) {
      notFound();
    }
    if (res.ok) {
      view = await res.json();
    }
  } catch {
    view = undefined;
  }

  if (!view) {
    return (
      <div className="py-8">
        <p className="card p-6 text-sm text-ivory-muted">Can&apos;t reach the Hetu API at {API_URL}.</p>
      </div>
    );
  }

  const { case: info } = view;

  return (
    <div className="flex flex-col gap-14 py-4">
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-md border border-amber-800 bg-amber-950/40 p-4">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-amber-400">
            Admin Preview Mode
          </span>
          <p className="text-sm text-ivory-muted">
            Status: <span className="text-ivory font-medium">{info.status}</span> • Review State:{" "}
            <span className="text-ivory font-medium">{info.review_state}</span>
          </p>
        </div>
        <Link
          href="/admin"
          className="rounded border border-gold-line bg-surface-raised px-3 py-1.5 text-xs text-ivory hover:text-gold transition-colors"
        >
          ← Back to Admin Console
        </Link>
      </div>

      <header className="flex flex-col gap-3">
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
