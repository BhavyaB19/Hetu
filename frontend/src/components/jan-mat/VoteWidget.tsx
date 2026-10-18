"use client";

import { useState } from "react";
import type { PollResultsView, VoteRequest } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";

const REASON_OPTIONS = [
  "Sentence too lenient",
  "Sentence too harsh",
  "Justice was delayed",
  "Evidence was handled well",
  "Evidence was handled poorly",
  "Procedure was fair",
  "Media pressure affected it",
  "Other",
];

interface VoteWidgetProps {
  pollId: string;
  isClosed?: boolean;
  initialResults: PollResultsView;
  onVoteSuccess?: (results: PollResultsView) => void;
}

export function VoteWidget({
  pollId,
  isClosed = false,
  initialResults,
  onVoteSuccess,
}: VoteWidgetProps) {
  const { showToast } = useToast();
  const [selectedChoice, setSelectedChoice] = useState<"agree" | "partial" | "disagree" | null>(null);
  const [selectedReasons, setSelectedReasons] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [hasVoted, setHasVoted] = useState(false);

  const toggleReason = (reason: string) => {
    setSelectedReasons((prev) =>
      prev.includes(reason) ? prev.filter((r) => r !== reason) : [...prev, reason]
    );
  };

  const handleVote = async (choice: "agree" | "partial" | "disagree") => {
    if (isClosed || isSubmitting) return;

    setSelectedChoice(choice);
    setIsSubmitting(true);

    // Optimistic calculation for rollback state
    const prevResults = { ...initialResults };
    const optimisticResults: PollResultsView = {
      ...initialResults,
      total_votes: initialResults.total_votes + (hasVoted ? 0 : 1),
      agree: initialResults.agree + (choice === "agree" ? 1 : 0),
      partial: initialResults.partial + (choice === "partial" ? 1 : 0),
      disagree: initialResults.disagree + (choice === "disagree" ? 1 : 0),
      agree_pct: 0,
      partial_pct: 0,
      disagree_pct: 0,
      top_reasons: initialResults.top_reasons,
    };
    const total = optimisticResults.total_votes || 1;
    optimisticResults.agree_pct = Math.round((optimisticResults.agree / total) * 100);
    optimisticResults.partial_pct = Math.round((optimisticResults.partial / total) * 100);
    optimisticResults.disagree_pct = Math.round((optimisticResults.disagree / total) * 100);

    // Optimistically update parent
    onVoteSuccess?.(optimisticResults);

    try {
      const payload: VoteRequest = {
        choice,
        reasons: selectedReasons,
      };

      const res = await fetch(`/api/polls/${pollId}/vote`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to record vote");
      }

      const updatedResults: PollResultsView = await res.json();
      setHasVoted(true);
      onVoteSuccess?.(updatedResults);
      showToast("Your perspective has been anonymously recorded.", {
        type: "success",
        title: "Ballot Cast",
      });
    } catch (err: unknown) {
      // Rollback on error
      onVoteSuccess?.(prevResults);
      const msg = err instanceof Error ? err.message : "Vote could not be processed";
      showToast(msg, { type: "error", title: "Submission Error" });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="card p-6 sm:p-8 bg-surface border-gold-line flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="eyebrow text-gold text-[10px]">Deliberative Ballot</span>
          {isClosed && (
            <span className="text-xs font-semibold uppercase text-danger border border-danger/40 bg-danger/10 px-2 py-0.5 rounded">
              Ballot Closed
            </span>
          )}
        </div>
        <h3 className="font-serif text-2xl text-ivory">
          Do you agree with the court&apos;s verdict?
        </h3>
        <p className="text-xs text-ivory-muted leading-relaxed">
          Tap an option to cast your vote. You may change your vote at any time.
        </p>
      </div>

      {/* Primary Tap Buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <button
          type="button"
          disabled={isClosed || isSubmitting}
          onClick={() => handleVote("agree")}
          className={`flex flex-col items-center justify-center p-4 rounded-lg border text-center transition-all cursor-pointer ${
            selectedChoice === "agree"
              ? "border-ok bg-ok/15 text-ivory font-semibold ring-1 ring-ok"
              : "border-gold-line bg-surface hover:border-gold hover:bg-gold-soft/20 text-ivory-muted hover:text-ivory"
          }`}
        >
          <span className="text-base font-serif font-bold text-ivory">Agree</span>
          <span className="text-[11px] text-ivory-faint mt-1">Findings &amp; sentence sound</span>
        </button>

        <button
          type="button"
          disabled={isClosed || isSubmitting}
          onClick={() => handleVote("partial")}
          className={`flex flex-col items-center justify-center p-4 rounded-lg border text-center transition-all cursor-pointer ${
            selectedChoice === "partial"
              ? "border-gold bg-gold-soft text-ivory font-semibold ring-1 ring-gold"
              : "border-gold-line bg-surface hover:border-gold hover:bg-gold-soft/20 text-ivory-muted hover:text-ivory"
          }`}
        >
          <span className="text-base font-serif font-bold text-ivory">Partly Agree</span>
          <span className="text-[11px] text-ivory-faint mt-1">Agree with facts, disagree with sentence</span>
        </button>

        <button
          type="button"
          disabled={isClosed || isSubmitting}
          onClick={() => handleVote("disagree")}
          className={`flex flex-col items-center justify-center p-4 rounded-lg border text-center transition-all cursor-pointer ${
            selectedChoice === "disagree"
              ? "border-danger bg-danger/15 text-ivory font-semibold ring-1 ring-danger"
              : "border-gold-line bg-surface hover:border-gold hover:bg-gold-soft/20 text-ivory-muted hover:text-ivory"
          }`}
        >
          <span className="text-base font-serif font-bold text-ivory">Disagree</span>
          <span className="text-[11px] text-ivory-faint mt-1">Verdict or reasoning flawed</span>
        </button>
      </div>

      {/* Reason Chips (Optional Multi-Select) */}
      <div className="flex flex-col gap-2.5 pt-2 border-t border-gold-line/40">
        <label className="text-xs font-semibold text-ivory-muted">
          What factors influenced your stance? (Optional, select all that apply)
        </label>
        <div className="flex flex-wrap gap-2">
          {REASON_OPTIONS.map((reason) => {
            const isSelected = selectedReasons.includes(reason);
            return (
              <button
                key={reason}
                type="button"
                disabled={isClosed || isSubmitting}
                onClick={() => toggleReason(reason)}
                className={`text-xs px-3 py-1.5 rounded-full border transition-all cursor-pointer ${
                  isSelected
                    ? "border-gold bg-gold text-ink font-semibold"
                    : "border-gold-line/60 bg-gold-soft/20 text-ivory-muted hover:border-gold hover:text-ivory"
                }`}
              >
                {reason}
              </button>
            );
          })}
        </div>
      </div>

      {/* Disclaimers & Not a Representative Sample */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-3 border-t border-gold-line/40 text-[11px] text-ivory-faint">
        <div className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-gold shrink-0" />
          <span>
            <strong>Not a representative sample:</strong> Reflects digital engagement, not demographic census data.
          </span>
        </div>
        <span className="shrink-0 text-ivory-faint">
          One vote per device · Hashed token
        </span>
      </div>
    </div>
  );
}
