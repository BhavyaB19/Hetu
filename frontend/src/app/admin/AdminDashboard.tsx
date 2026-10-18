"use client";

import Link from "next/link";
import { useState } from "react";

import type { CaseSummary } from "@/lib/api";

export function AdminDashboard({ initialCases }: { initialCases: CaseSummary[] }) {
  const [cases, setCases] = useState<CaseSummary[]>(initialCases);
  const [loadingSlug, setLoadingSlug] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function togglePublish(c: CaseSummary) {
    const nextState = c.review_state === "published" ? "draft" : "published";
    setLoadingSlug(c.slug);
    setError(null);
    try {
      const res = await fetch(`/api/admin/cases/${encodeURIComponent(c.slug)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ review_state: nextState }),
      });
      if (!res.ok) {
        throw new Error("Failed to update publication status");
      }
      const updated = await res.json();
      setCases((prev) => prev.map((item) => (item.slug === c.slug ? { ...item, ...updated } : item)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error updating case");
    } finally {
      setLoadingSlug(null);
    }
  }

  async function toggleFeatured(c: CaseSummary) {
    const nextFeatured = !c.featured;
    setLoadingSlug(c.slug);
    setError(null);
    try {
      const res = await fetch(`/api/admin/cases/${encodeURIComponent(c.slug)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ featured: nextFeatured }),
      });
      if (!res.ok) {
        throw new Error("Failed to update featured flag");
      }
      const updated = await res.json();
      setCases((prev) => prev.map((item) => (item.slug === c.slug ? { ...item, ...updated } : item)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error updating featured flag");
    } finally {
      setLoadingSlug(null);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="eyebrow">Administration</p>
          <h1 className="font-serif text-3xl text-ivory">Case Management</h1>
        </div>
        <Link
          href="/admin/cases/new"
          className="rounded-md bg-gold px-4 py-2 text-sm font-semibold text-ink transition-colors hover:bg-bronze"
        >
          + Ingest New Case
        </Link>
      </div>

      {error && (
        <div role="alert" className="card border-danger p-4 text-sm text-danger">
          {error}
        </div>
      )}

      {cases.length === 0 ? (
        <div className="card p-8 text-center text-ivory-muted">
          No cases in database. Click &ldquo;+ Ingest New Case&rdquo; to start ingestion.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gold-line bg-surface">
          <table className="w-full text-left text-sm text-ivory">
            <thead className="border-b border-gold-line bg-surface-raised text-xs uppercase tracking-wider text-ivory-muted">
              <tr>
                <th scope="col" className="px-5 py-3">Case</th>
                <th scope="col" className="px-5 py-3">Status</th>
                <th scope="col" className="px-5 py-3">Review State</th>
                <th scope="col" className="px-5 py-3">Featured</th>
                <th scope="col" className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gold-line">
              {cases.map((c) => {
                const busy = loadingSlug === c.slug;
                return (
                  <tr key={c.slug} className="hover:bg-surface-raised/40">
                    <td className="px-5 py-4">
                      <div className="font-medium text-ivory">{c.title}</div>
                      <div className="text-xs text-ivory-muted">
                        {c.category} {c.court ? `• ${c.court}` : ""}
                        {c.is_illustrative && <span className="ml-2 text-gold">(Illustrative)</span>}
                      </div>
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={`inline-flex rounded px-2 py-0.5 text-xs font-semibold ${
                          c.status === "decided"
                            ? "bg-emerald-950/70 text-emerald-400 border border-emerald-800"
                            : "bg-amber-950/70 text-amber-400 border border-amber-800"
                        }`}
                      >
                        {c.status}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={`inline-flex rounded px-2 py-0.5 text-xs font-semibold ${
                          c.review_state === "published"
                            ? "bg-gold/20 text-gold border border-gold/40"
                            : "bg-surface-raised text-ivory-muted border border-gold-line"
                        }`}
                      >
                        {c.review_state}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <button
                        type="button"
                        onClick={() => toggleFeatured(c)}
                        disabled={busy}
                        className={`text-xs px-2 py-1 rounded border transition-colors ${
                          c.featured
                            ? "bg-gold text-ink border-gold font-semibold"
                            : "border-gold-line text-ivory-muted hover:text-ivory"
                        }`}
                      >
                        {c.featured ? "Featured ★" : "Make Featured"}
                      </button>
                    </td>
                    <td className="px-5 py-4 text-right space-x-2">
                      <Link
                        href={`/admin/cases/${encodeURIComponent(c.slug)}/preview`}
                        className="text-xs text-ivory-muted hover:text-gold transition-colors"
                      >
                        Preview
                      </Link>
                      <button
                        type="button"
                        onClick={() => togglePublish(c)}
                        disabled={busy}
                        className={`text-xs font-semibold px-2.5 py-1 rounded transition-colors ${
                          c.review_state === "published"
                            ? "bg-surface-raised border border-gold-line text-ivory hover:border-danger hover:text-danger"
                            : "bg-gold text-ink hover:bg-bronze"
                        }`}
                      >
                        {busy ? "Saving…" : c.review_state === "published" ? "Unpublish" : "Publish"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
