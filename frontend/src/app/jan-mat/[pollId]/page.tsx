import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";

import { PollDeliberationClient } from "@/components/jan-mat/PollDeliberationClient";
import { ErrorState } from "@/components/ui/ErrorState";
import { api, type PollView, type PollResultsView } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ pollId: string }>;
}): Promise<Metadata> {
  const { pollId } = await params;
  const { data: poll } = await api
    .GET("/polls/{poll_id}", { params: { path: { poll_id: pollId } } })
    .catch(() => ({ data: undefined }));

  if (!poll) {
    return { title: "Public Ballot | Jan Mat | Hetu" };
  }

  return {
    title: `${poll.question} — Jan Mat Ballot | Hetu`,
    description: `Deliberate on ${poll.case_title || "published court judgment"}. Cast an anonymous vote and share perspectives on evidence and reasoning.`,
  };
}

export default async function PollDetailPage({
  params,
}: {
  params: Promise<{ pollId: string }>;
}) {
  const { pollId } = await params;

  // Fetch poll and results in parallel
  const [pollRes, resultsRes] = await Promise.all([
    api.GET("/polls/{poll_id}", { params: { path: { poll_id: pollId } } }).catch(() => ({ data: undefined, response: undefined })),
    api.GET("/polls/{poll_id}/results", { params: { path: { poll_id: pollId } } }).catch(() => ({ data: undefined, response: undefined })),
  ]);

  if (pollRes.response?.status === 404) notFound();

  if (!pollRes.data || !resultsRes.data) {
    return (
      <ErrorState
        eyebrow="Ballot Lookup Error"
        title="Unable to load public ballot"
        message="The requested Jan Mat ballot could not be retrieved from the Hetu database. Ensure the backend service is running."
      />
    );
  }

  const poll = pollRes.data as PollView;
  const results = resultsRes.data as PollResultsView;

  // Optional: fetch case summary if case_slug is present
  let caseSummary: string | null = null;
  if (poll.case_slug) {
    const caseRes = await api
      .GET("/cases/{slug}", { params: { path: { slug: poll.case_slug } } })
      .catch(() => ({ data: undefined }));
    if (caseRes.data?.case?.summary) {
      caseSummary = caseRes.data.case.summary;
    }
  }

  return (
    <div className="flex flex-col gap-10 py-6">
      {/* Header */}
      <header className="flex flex-col gap-4 border-b border-gold-line pb-6">
        <Link
          href="/jan-mat"
          className="text-xs text-ivory-muted hover:text-gold transition-colors inline-flex items-center gap-1"
        >
          <span>← All Jan Mat Ballots</span>
        </Link>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="eyebrow text-gold text-[10px]">Democratic Deliberation</span>
            {poll.case_title && (
              <span className="text-xs text-ivory-faint">· Case: {poll.case_title}</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {poll.status === "open" ? (
              <span className="inline-flex items-center gap-1 rounded bg-ok/10 border border-ok/40 px-2 py-0.5 text-[10px] font-semibold text-ok uppercase tracking-wider">
                <span className="h-1.5 w-1.5 rounded-full bg-ok animate-pulse" />
                Open for voting
              </span>
            ) : (
              <span className="rounded bg-track border border-gold-line/40 px-2 py-0.5 text-[10px] font-semibold text-ivory-faint uppercase tracking-wider">
                Ballot Concluded
              </span>
            )}
          </div>
        </div>

        <h1 className="font-serif text-3xl sm:text-5xl text-ivory leading-tight">
          {poll.question}
        </h1>

        {/* Plain-Language Summary Box */}
        {caseSummary && (
          <div className="card p-5 bg-gold-soft/10 border-gold-line flex flex-col gap-2 mt-2">
            <div className="flex items-center justify-between">
              <span className="eyebrow text-gold text-[10px]">What the Court Decided, in Simple Terms</span>
              {poll.case_slug && (
                <Link
                  href={`/verdicts/${poll.case_slug}`}
                  className="text-xs text-gold hover:text-ivory transition-colors font-medium"
                >
                  View Full Verdict &amp; Evidence →
                </Link>
              )}
            </div>
            <p className="text-xs sm:text-sm text-ivory-muted leading-relaxed">
              {caseSummary}
            </p>
          </div>
        )}
      </header>

      {/* Deliberation Client: LiveScales + VoteWidget + ResultsBars + CommentThread */}
      <PollDeliberationClient poll={poll} initialResults={results} />
    </div>
  );
}
