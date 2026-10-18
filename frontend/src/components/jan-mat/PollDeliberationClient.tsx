"use client";

import { useState } from "react";
import type { PollView, PollResultsView } from "@/lib/api";
import { LiveScales } from "./LiveScales";
import { VoteWidget } from "./VoteWidget";
import { ResultsBars } from "./ResultsBars";
import { CommentThread } from "./CommentThread";

interface PollDeliberationClientProps {
  poll: PollView;
  initialResults: PollResultsView;
}

export function PollDeliberationClient({
  poll,
  initialResults,
}: PollDeliberationClientProps) {
  const [results, setResults] = useState<PollResultsView>(initialResults);

  return (
    <div className="flex flex-col gap-10">
      {/* Visual Scales & Voting Section */}
      <div className="grid gap-6 lg:grid-cols-12 items-start">
        {/* Left Column: Live SVG Scales */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          <LiveScales
            agree={results.agree}
            partial={results.partial}
            disagree={results.disagree}
            totalVotes={results.total_votes}
          />

          <div className="card p-4 bg-surface/60 border-gold-line/40 text-xs text-ivory-muted leading-relaxed">
            <p className="font-semibold text-gold mb-1">Deliberation Protocol</p>
            <p>
              Partly agree counts half toward each side of the scale. Cast your ballot based on judicial reasoning and evidentiary standards.
            </p>
          </div>
        </div>

        {/* Right Column: VoteWidget & Results */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          <VoteWidget
            pollId={poll.id}
            isClosed={poll.status === "closed"}
            initialResults={results}
            onVoteSuccess={setResults}
          />

          <ResultsBars
            pollId={poll.id}
            results={results}
            onUpdateResults={setResults}
          />
        </div>
      </div>

      {/* Comment Thread */}
      <CommentThread pollId={poll.id} />
    </div>
  );
}
