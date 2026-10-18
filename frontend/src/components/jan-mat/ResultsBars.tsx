"use client";

import { useEffect, useState } from "react";
import type { PollResultsView } from "@/lib/api";

interface ResultsBarsProps {
  pollId: string;
  results: PollResultsView;
  onUpdateResults?: (results: PollResultsView) => void;
}

export function ResultsBars({
  pollId,
  results,
  onUpdateResults,
}: ResultsBarsProps) {
  const [liveResults, setLiveResults] = useState<PollResultsView>(results);

  // Sync with prop when parent updates (e.g. from optimistic vote)
  useEffect(() => {
    setLiveResults(results);
  }, [results]);

  // 10-second polling for live results
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/polls/${pollId}/results`);
        if (res.ok) {
          const fresh: PollResultsView = await res.json();
          setLiveResults(fresh);
          onUpdateResults?.(fresh);
        }
      } catch {
        // Silently continue polling on network hiccups
      }
    }, 10000);

    return () => clearInterval(interval);
  }, [pollId, onUpdateResults]);

  const total = liveResults.total_votes;
  const agreePct = Math.round(liveResults.agree_pct || (total > 0 ? (liveResults.agree / total) * 100 : 0));
  const partialPct = Math.round(liveResults.partial_pct || (total > 0 ? (liveResults.partial / total) * 100 : 0));
  const disagreePct = Math.round(liveResults.disagree_pct || (total > 0 ? (liveResults.disagree / total) * 100 : 0));

  return (
    <div
      className="card p-6 sm:p-8 bg-surface border-gold-line flex flex-col gap-6"
      aria-label="Ballot results and vote share breakdown"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gold-line/40 pb-4">
        <div>
          <span className="eyebrow text-gold text-[10px]">Tally &amp; Consensus</span>
          <h3 className="font-serif text-2xl text-ivory">Ballot Results</h3>
        </div>
        <div
          aria-live="polite"
          className="flex items-center gap-2 text-xs font-mono text-ivory-muted"
        >
          <span className="h-2 w-2 rounded-full bg-ok animate-pulse" />
          <span>{total.toLocaleString()} total votes cast</span>
        </div>
      </div>

      {/* 3 Main Result Bars */}
      <div className="flex flex-col gap-4">
        {/* Agree */}
        <div className="flex flex-col gap-1.5">
          <div className="flex justify-between items-center text-xs">
            <span className="font-medium text-ivory flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-ok shrink-0" />
              <span>Agree with Verdict</span>
            </span>
            <span className="font-mono font-semibold text-ivory">
              {agreePct}% ({liveResults.agree})
            </span>
          </div>
          <div className="h-3 w-full rounded-full bg-track overflow-hidden">
            <div
              className="h-full rounded-full bg-ok transition-all duration-700 ease-out"
              style={{ width: `${agreePct}%` }}
              role="progressbar"
              aria-valuenow={agreePct}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Agree percentage"
            />
          </div>
        </div>

        {/* Partly Agree */}
        <div className="flex flex-col gap-1.5">
          <div className="flex justify-between items-center text-xs">
            <span className="font-medium text-ivory flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-gold shrink-0" />
              <span>Partly Agree</span>
            </span>
            <span className="font-mono font-semibold text-ivory">
              {partialPct}% ({liveResults.partial})
            </span>
          </div>
          <div className="h-3 w-full rounded-full bg-track overflow-hidden">
            <div
              className="h-full rounded-full bg-gold transition-all duration-700 ease-out"
              style={{ width: `${partialPct}%` }}
              role="progressbar"
              aria-valuenow={partialPct}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Partly agree percentage"
            />
          </div>
        </div>

        {/* Disagree */}
        <div className="flex flex-col gap-1.5">
          <div className="flex justify-between items-center text-xs">
            <span className="font-medium text-ivory flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-danger shrink-0" />
              <span>Disagree with Verdict</span>
            </span>
            <span className="font-mono font-semibold text-ivory">
              {disagreePct}% ({liveResults.disagree})
            </span>
          </div>
          <div className="h-3 w-full rounded-full bg-track overflow-hidden">
            <div
              className="h-full rounded-full bg-danger transition-all duration-700 ease-out"
              style={{ width: `${disagreePct}%` }}
              role="progressbar"
              aria-valuenow={disagreePct}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Disagree percentage"
            />
          </div>
        </div>
      </div>

      {/* Top Reasons Breakdown */}
      {liveResults.top_reasons && liveResults.top_reasons.length > 0 && (
        <div className="flex flex-col gap-3 pt-3 border-t border-gold-line/40">
          <span className="eyebrow text-gold text-[10px]">Dominant Deliberation Factors</span>
          <div className="grid gap-2 sm:grid-cols-2">
            {liveResults.top_reasons.map((item) => (
              <div
                key={item.reason}
                className="flex items-center justify-between p-2.5 rounded bg-gold-soft/20 border border-gold-line/40 text-xs"
              >
                <span className="text-ivory-muted truncate pr-2">{item.reason}</span>
                <span className="font-mono font-bold text-gold shrink-0">
                  {item.count} {item.count === 1 ? "vote" : "votes"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Live Polling Stamp & Notice */}
      <div className="flex items-center justify-between text-[11px] text-ivory-faint pt-2 border-t border-gold-line/40">
        <span>Updates live every 10 seconds</span>
        <span className="italic text-ivory-muted">Not a representative sample</span>
      </div>
    </div>
  );
}
