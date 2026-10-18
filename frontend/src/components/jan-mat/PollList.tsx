"use client";

import { useState } from "react";
import Link from "next/link";
import type { PollView } from "@/lib/api";
import { date } from "@/lib/format";

interface PollListProps {
  polls: PollView[];
}

export function PollList({ polls }: PollListProps) {
  const [filter, setFilter] = useState<"all" | "open" | "closed">("all");
  const [sort, setSort] = useState<"trending" | "newest" | "featured">("trending");

  // Filtering
  const filtered = polls.filter((p) => {
    if (filter === "open") return p.status === "open";
    if (filter === "closed") return p.status === "closed";
    return true;
  });

  // Sorting
  const sorted = [...filtered].sort((a, b) => {
    if (sort === "featured") {
      if (a.featured !== b.featured) return a.featured ? -1 : 1;
      return b.total_votes - a.total_votes;
    }
    if (sort === "newest") {
      return new Date(b.opens_at).getTime() - new Date(a.opens_at).getTime();
    }
    // Trending
    return b.total_votes - a.total_votes;
  });

  return (
    <div className="flex flex-col gap-6">
      {/* Controls Bar: Filters & Sort Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gold-line/40 pb-4">
        {/* Status Filters */}
        <div className="flex items-center gap-1.5 p-1 rounded-md bg-surface border border-gold-line/40 text-xs">
          <button
            type="button"
            onClick={() => setFilter("all")}
            className={`px-3 py-1 rounded font-medium transition-colors cursor-pointer ${
              filter === "all" ? "bg-gold text-ink font-semibold" : "text-ivory-muted hover:text-ivory"
            }`}
          >
            All Ballots ({polls.length})
          </button>
          <button
            type="button"
            onClick={() => setFilter("open")}
            className={`px-3 py-1 rounded font-medium transition-colors cursor-pointer ${
              filter === "open" ? "bg-gold text-ink font-semibold" : "text-ivory-muted hover:text-ivory"
            }`}
          >
            Open ({polls.filter((p) => p.status === "open").length})
          </button>
          <button
            type="button"
            onClick={() => setFilter("closed")}
            className={`px-3 py-1 rounded font-medium transition-colors cursor-pointer ${
              filter === "closed" ? "bg-gold text-ink font-semibold" : "text-ivory-muted hover:text-ivory"
            }`}
          >
            Closed ({polls.filter((p) => p.status === "closed").length})
          </button>
        </div>

        {/* Sort Tabs */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-ivory-faint">Sort:</span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setSort("trending")}
              className={`px-2.5 py-1 rounded transition-colors cursor-pointer ${
                sort === "trending" ? "text-gold font-semibold underline decoration-gold" : "text-ivory-muted hover:text-ivory"
              }`}
            >
              Trending
            </button>
            <span className="text-ivory-faint">·</span>
            <button
              type="button"
              onClick={() => setSort("newest")}
              className={`px-2.5 py-1 rounded transition-colors cursor-pointer ${
                sort === "newest" ? "text-gold font-semibold underline decoration-gold" : "text-ivory-muted hover:text-ivory"
              }`}
            >
              Newest
            </button>
            <span className="text-ivory-faint">·</span>
            <button
              type="button"
              onClick={() => setSort("featured")}
              className={`px-2.5 py-1 rounded transition-colors cursor-pointer ${
                sort === "featured" ? "text-gold font-semibold underline decoration-gold" : "text-ivory-muted hover:text-ivory"
              }`}
            >
              Featured
            </button>
          </div>
        </div>
      </div>

      {/* Grid of Poll Cards */}
      {sorted.length === 0 ? (
        <div className="card p-12 text-center text-sm text-ivory-muted">
          No ballots match the selected filter.
        </div>
      ) : (
        <div className="grid gap-5 md:grid-cols-2">
          {sorted.map((poll) => (
            <article
              key={poll.id}
              className="card flex flex-col justify-between gap-5 p-6 border-gold-line hover:border-gold hover:bg-gold-soft/10 transition-all group"
            >
              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {poll.status === "open" ? (
                      <span className="inline-flex items-center gap-1 rounded bg-ok/10 border border-ok/40 px-2 py-0.5 text-[10px] font-semibold text-ok uppercase tracking-wider">
                        <span className="h-1.5 w-1.5 rounded-full bg-ok animate-pulse" />
                        Open Ballot
                      </span>
                    ) : (
                      <span className="rounded bg-track border border-gold-line/40 px-2 py-0.5 text-[10px] font-semibold text-ivory-faint uppercase tracking-wider">
                        Closed
                      </span>
                    )}
                    {poll.featured && (
                      <span className="rounded bg-gold-soft border border-gold-line px-2 py-0.5 text-[10px] font-semibold text-gold">
                        Featured
                      </span>
                    )}
                  </div>
                  <span className="text-[11px] font-mono text-ivory-muted">
                    {poll.total_votes.toLocaleString()} {poll.total_votes === 1 ? "vote" : "votes"}
                  </span>
                </div>

                <div>
                  {poll.case_title && (
                    <p className="eyebrow text-gold text-[10px] mb-1">
                      Case: {poll.case_title}
                    </p>
                  )}
                  <h3 className="font-serif text-xl sm:text-2xl text-ivory group-hover:text-gold transition-colors">
                    {poll.question}
                  </h3>
                </div>

                <div className="flex items-center gap-2 text-[11px] text-ivory-faint pt-1">
                  <span>Opened {date(poll.opens_at)}</span>
                  {poll.closes_at && <span>· Closes {date(poll.closes_at)}</span>}
                </div>
              </div>

              <div className="border-t border-gold-line/40 pt-4 flex items-center justify-between">
                {poll.case_slug ? (
                  <Link
                    href={`/verdicts/${poll.case_slug}`}
                    className="text-xs text-ivory-muted hover:text-gold transition-colors"
                  >
                    ← Read Judgment
                  </Link>
                ) : (
                  <span className="text-xs text-ivory-faint">Decided Case</span>
                )}
                <Link
                  href={`/jan-mat/${poll.id}`}
                  className="rounded-md bg-gold px-4 py-1.5 text-xs font-semibold text-ink hover:bg-bronze transition-colors shadow-sm"
                >
                  {poll.status === "open" ? "Vote & Deliberate →" : "View Final Results →"}
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
