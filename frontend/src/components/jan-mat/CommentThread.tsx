"use client";

import { useEffect, useState, useCallback } from "react";
import type { CommentView, CommentRequest } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { date } from "@/lib/format";

interface CommentThreadProps {
  pollId: string;
}

export function CommentThread({ pollId }: CommentThreadProps) {
  const { showToast } = useToast();
  const [comments, setComments] = useState<CommentView[]>([]);
  const [sort, setSort] = useState<"top" | "new">("top");
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // New comment input
  const [newBody, setNewBody] = useState("");
  const [newHandle, setNewHandle] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [heldNotice, setHeldNotice] = useState<string | null>(null);

  // Reply input state: parentId -> { body, handle }
  const [replyingTo, setReplyingTo] = useState<string | null>(null);
  const [replyBody, setReplyBody] = useState("");
  const [replyHandle, setReplyHandle] = useState("");
  const [isSubmittingReply, setIsSubmittingReply] = useState(false);

  // Report dialog state
  const [reportingCommentId, setReportingCommentId] = useState<string | null>(null);
  const [reportReason, setReportReason] = useState("");
  const [isSubmittingReport, setIsSubmittingReport] = useState(false);

  const fetchComments = useCallback(async (currentSort: "top" | "new") => {
    try {
      const res = await fetch(`/api/polls/${pollId}/comments?sort=${currentSort}`);
      if (res.ok) {
        const data: CommentView[] = await res.json();
        setComments(data);
      }
    } catch {
      // Keep existing comments on error
    } finally {
      setIsLoading(false);
    }
  }, [pollId]);

  useEffect(() => {
    setIsLoading(true);
    fetchComments(sort);
  }, [fetchComments, sort]);

  const handlePostComment = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = newBody.trim();
    if (text.length < 3 || text.length > 800) {
      showToast("Comments must be between 3 and 800 characters.", { type: "warning" });
      return;
    }

    setIsSubmitting(true);
    setHeldNotice(null);

    try {
      const payload: CommentRequest = {
        body: text,
        handle: newHandle.trim() || undefined,
      };

      const res = await fetch(`/api/polls/${pollId}/comments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to post comment");
      }

      const created: CommentView = await res.json();
      setNewBody("");

      if (created.status === "held") {
        setHeldNotice(
          "Your comment has been held for review by our automated moderation filters (checking for privacy of individuals, abusive language, or contempt). It will be reviewed by human moderators before publication."
        );
        showToast("Comment submitted and held for moderation review.", {
          type: "warning",
          title: "Held for Review",
        });
      } else {
        setComments((prev) => [created, ...prev]);
        showToast("Your comment has been published.", {
          type: "success",
          title: "Comment Posted",
        });
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error posting comment";
      showToast(msg, { type: "error", title: "Posting Failed" });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePostReply = async (parentId: string) => {
    const text = replyBody.trim();
    if (text.length < 3 || text.length > 800) {
      showToast("Replies must be between 3 and 800 characters.", { type: "warning" });
      return;
    }

    setIsSubmittingReply(true);

    try {
      const payload: CommentRequest = {
        body: text,
        parent_id: parentId,
        handle: replyHandle.trim() || undefined,
      };

      const res = await fetch(`/api/polls/${pollId}/comments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to post reply");
      }

      const created: CommentView = await res.json();
      setReplyBody("");
      setReplyingTo(null);

      if (created.status === "held") {
        showToast(
          "Your reply has been held for review by automated filters and will be reviewed shortly.",
          { type: "warning", title: "Held for Review" }
        );
      } else {
        // Attach reply to parent in local state
        setComments((prev) =>
          prev.map((c) =>
            c.id === parentId ? { ...c, replies: [...(c.replies || []), created] } : c
          )
        );
        showToast("Your reply has been published.", { type: "success" });
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error submitting reply";
      showToast(msg, { type: "error" });
    } finally {
      setIsSubmittingReply(false);
    }
  };

  const handleUpvote = async (commentId: string) => {
    try {
      const res = await fetch(`/api/comments/${commentId}/upvote`, {
        method: "POST",
      });

      if (!res.ok) {
        throw new Error("Unable to record upvote");
      }

      const data = await res.json();
      // Update count locally across top-level and nested replies
      setComments((prev) =>
        prev.map((c) => {
          if (c.id === commentId) {
            return { ...c, upvotes: data.upvotes };
          }
          if (c.replies) {
            return {
              ...c,
              replies: c.replies.map((r) => (r.id === commentId ? { ...r, upvotes: data.upvotes } : r)),
            };
          }
          return c;
        })
      );

      showToast(data.upvoted ? "Upvote recorded" : "Upvote removed", { type: "info" });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error upvoting";
      showToast(msg, { type: "error" });
    }
  };

  const handleReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reportingCommentId || reportReason.trim().length < 3) {
      showToast("Please provide a reason of at least 3 characters.", { type: "warning" });
      return;
    }

    setIsSubmittingReport(true);

    try {
      const res = await fetch(`/api/comments/${reportingCommentId}/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: reportReason.trim() }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Unable to submit report");
      }

      showToast("Thank you. The comment has been flagged for editorial review.", {
        type: "success",
        title: "Comment Reported",
      });
      setReportingCommentId(null);
      setReportReason("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Reporting failed";
      showToast(msg, { type: "error" });
    } finally {
      setIsSubmittingReport(false);
    }
  };

  return (
    <section className="card p-6 sm:p-8 bg-surface border-gold-line flex flex-col gap-6" aria-label="Public Discourse">
      {/* Thread Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gold-line/40 pb-4">
        <div>
          <span className="eyebrow text-gold text-[10px]">Deliberative Discourse</span>
          <h3 className="font-serif text-2xl text-ivory">Public Perspectives</h3>
        </div>

        {/* Sort Controls */}
        <div className="flex items-center gap-1.5 p-1 rounded-md bg-ink border border-gold-line/40 text-xs">
          <button
            type="button"
            onClick={() => setSort("top")}
            className={`px-3 py-1 rounded font-medium transition-colors cursor-pointer ${
              sort === "top" ? "bg-gold-soft text-gold font-semibold" : "text-ivory-muted hover:text-ivory"
            }`}
          >
            Top Voted
          </button>
          <button
            type="button"
            onClick={() => setSort("new")}
            className={`px-3 py-1 rounded font-medium transition-colors cursor-pointer ${
              sort === "new" ? "bg-gold-soft text-gold font-semibold" : "text-ivory-muted hover:text-ivory"
            }`}
          >
            Newest First
          </button>
        </div>
      </div>

      {/* Held for Review Alert */}
      {heldNotice && (
        <div
          role="alert"
          className="p-4 rounded-md border border-gold/60 bg-gold-soft/30 text-xs text-ivory leading-relaxed flex items-start gap-3"
        >
          <svg className="h-5 w-5 text-gold shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div className="flex-1">
            <p className="font-semibold text-gold mb-1">Comment Held for Review</p>
            <p className="text-ivory-muted">{heldNotice}</p>
          </div>
          <button
            type="button"
            onClick={() => setHeldNotice(null)}
            className="text-ivory-faint hover:text-ivory text-sm cursor-pointer"
          >
            ✕
          </button>
        </div>
      )}

      {/* New Top-Level Comment Form */}
      <form onSubmit={handlePostComment} className="flex flex-col gap-3 p-4 rounded-lg border border-gold-line/40 bg-ink/60">
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            placeholder="Anonymous handle (optional, e.g. Citizen 42)"
            value={newHandle}
            maxLength={50}
            onChange={(e) => setNewHandle(e.target.value)}
            className="sm:w-64 px-3 py-1.5 text-xs rounded border border-gold-line/60 bg-surface text-ivory placeholder-ivory-faint focus:outline-none focus:border-gold"
          />
          <p className="text-[11px] text-ivory-faint self-center">
            Private identities are automatically anonymized. Criticize reasoning, not people.
          </p>
        </div>

        <textarea
          rows={3}
          required
          minLength={3}
          maxLength={800}
          placeholder="Share your perspective on the judicial reasoning or evidence in this verdict (3–800 characters)..."
          value={newBody}
          onChange={(e) => setNewBody(e.target.value)}
          className="w-full p-3 text-xs rounded border border-gold-line/60 bg-surface text-ivory placeholder-ivory-faint focus:outline-none focus:border-gold leading-relaxed"
        />

        <div className="flex items-center justify-between">
          <span className={`text-[11px] font-mono ${newBody.length > 750 ? "text-danger" : "text-ivory-faint"}`}>
            {newBody.length}/800 characters
          </span>
          <button
            type="submit"
            disabled={isSubmitting || newBody.trim().length < 3}
            className="rounded-md bg-gold px-4 py-1.5 text-xs font-semibold text-ink hover:bg-bronze transition-colors disabled:opacity-50 cursor-pointer"
          >
            {isSubmitting ? "Submitting..." : "Post Perspective"}
          </button>
        </div>
      </form>

      {/* Comments List */}
      {isLoading ? (
        <div className="py-8 text-center text-xs text-ivory-muted animate-pulse">
          Loading community perspectives...
        </div>
      ) : comments.length === 0 ? (
        <div className="py-8 text-center text-xs text-ivory-muted border border-gold-line/30 rounded-lg">
          No comments posted yet. Be the first to share a perspective on this verdict.
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {comments.map((comment) => (
            <article
              key={comment.id}
              className="p-4 rounded-lg border border-gold-line/40 bg-surface flex flex-col gap-3"
            >
              {/* Header: Handle, Date */}
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-gold">{comment.handle}</span>
                  <span className="text-[10px] text-ivory-faint">· {date(comment.created_at)}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setReportingCommentId(comment.id)}
                  className="text-[10px] text-ivory-faint hover:text-danger transition-colors cursor-pointer"
                >
                  Report
                </button>
              </div>

              {/* Body */}
              <p className="text-xs text-ivory leading-relaxed whitespace-pre-wrap">{comment.body}</p>

              {/* Actions: Upvote, Reply */}
              <div className="flex items-center gap-4 text-xs pt-1">
                <button
                  type="button"
                  onClick={() => handleUpvote(comment.id)}
                  className="inline-flex items-center gap-1.5 text-ivory-muted hover:text-gold transition-colors cursor-pointer"
                >
                  <span>▲</span>
                  <span className="font-mono font-medium">{comment.upvotes}</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setReplyingTo(replyingTo === comment.id ? null : comment.id);
                    setReplyBody("");
                  }}
                  className="text-ivory-faint hover:text-ivory transition-colors cursor-pointer"
                >
                  {replyingTo === comment.id ? "Cancel Reply" : "Reply"}
                </button>
              </div>

              {/* Nested Reply Form (1-level maximum) */}
              {replyingTo === comment.id && (
                <div className="mt-2 pl-4 border-l border-gold-line/50 flex flex-col gap-2">
                  <input
                    type="text"
                    placeholder="Anonymous handle (optional)"
                    value={replyHandle}
                    maxLength={50}
                    onChange={(e) => setReplyHandle(e.target.value)}
                    className="w-56 px-2.5 py-1 text-xs rounded border border-gold-line/60 bg-ink text-ivory placeholder-ivory-faint focus:outline-none focus:border-gold"
                  />
                  <textarea
                    rows={2}
                    placeholder={`Reply to ${comment.handle}...`}
                    value={replyBody}
                    maxLength={800}
                    onChange={(e) => setReplyBody(e.target.value)}
                    className="w-full p-2.5 text-xs rounded border border-gold-line/60 bg-ink text-ivory placeholder-ivory-faint focus:outline-none focus:border-gold"
                  />
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-ivory-faint">{replyBody.length}/800</span>
                    <button
                      type="button"
                      disabled={isSubmittingReply || replyBody.trim().length < 3}
                      onClick={() => handlePostReply(comment.id)}
                      className="rounded bg-gold px-3 py-1 text-xs font-semibold text-ink hover:bg-bronze transition-colors disabled:opacity-50 cursor-pointer"
                    >
                      {isSubmittingReply ? "Posting..." : "Post Reply"}
                    </button>
                  </div>
                </div>
              )}

              {/* Nested Replies Rendering (1-level) */}
              {comment.replies && comment.replies.length > 0 && (
                <div className="mt-3 pl-4 border-l border-gold-line/40 flex flex-col gap-3">
                  {comment.replies.map((reply) => (
                    <div key={reply.id} className="p-3 rounded bg-ink/40 border border-gold-line/20 flex flex-col gap-1.5">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-gold text-[11px]">{reply.handle}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] text-ivory-faint">{date(reply.created_at)}</span>
                          <button
                            type="button"
                            onClick={() => setReportingCommentId(reply.id)}
                            className="text-[9px] text-ivory-faint hover:text-danger cursor-pointer"
                          >
                            Report
                          </button>
                        </div>
                      </div>
                      <p className="text-xs text-ivory-muted leading-relaxed">{reply.body}</p>
                      <div className="pt-1 flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleUpvote(reply.id)}
                          className="inline-flex items-center gap-1 text-[11px] text-ivory-muted hover:text-gold cursor-pointer"
                        >
                          <span>▲</span>
                          <span className="font-mono">{reply.upvotes}</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </article>
          ))}
        </div>
      )}

      {/* Report Modal */}
      {reportingCommentId && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
        >
          <div className="card p-6 max-w-md w-full bg-surface border-gold-line flex flex-col gap-4">
            <h4 className="font-serif text-xl text-ivory">Report Comment</h4>
            <p className="text-xs text-ivory-muted leading-relaxed">
              Hetu enforces strict guidelines. Comments containing personal abuse, names of private individuals, or contemptuous threats will be hidden upon review.
            </p>
            <form onSubmit={handleReport} className="flex flex-col gap-3">
              <textarea
                required
                minLength={3}
                maxLength={500}
                rows={3}
                placeholder="Reason for reporting (e.g. personal attack, private name leak, abuse)..."
                value={reportReason}
                onChange={(e) => setReportReason(e.target.value)}
                className="w-full p-2.5 text-xs rounded border border-gold-line/60 bg-ink text-ivory placeholder-ivory-faint focus:outline-none focus:border-gold"
              />
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setReportingCommentId(null);
                    setReportReason("");
                  }}
                  className="px-3 py-1.5 text-xs text-ivory-muted hover:text-ivory cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingReport || reportReason.trim().length < 3}
                  className="rounded bg-danger px-4 py-1.5 text-xs font-semibold text-ivory hover:bg-danger/80 disabled:opacity-50 cursor-pointer"
                >
                  {isSubmittingReport ? "Reporting..." : "Submit Report"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}
