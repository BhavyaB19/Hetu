"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

const CATEGORIES = [
  "Criminal - Violent Crime",
  "Criminal - Financial / Corruption",
  "Constitutional",
  "Civil / Commercial",
  "Other",
];

export default function NewCasePage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [court, setCourt] = useState("");
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [status, setStatus] = useState<"decided" | "ongoing">("decided");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);

    try {
      const res = await fetch("/api/admin/cases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          court: court.trim() || null,
          category,
          status,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        const detail = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
        throw new Error(detail || "Failed to start case ingestion");
      }

      router.push(`/admin/jobs/${data.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error submitting case");
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl py-8">
      <div className="mb-6">
        <Link href="/admin" className="text-xs text-gold hover:text-bronze">
          ← Back to Admin Cases
        </Link>
        <p className="eyebrow mt-2">Ingestion</p>
        <h1 className="font-serif text-3xl text-ivory">Ingest New Case</h1>
        <p className="mt-1 text-sm text-ivory-muted">
          Start background collection and pipeline processing via TinyFish agents.
        </p>
      </div>

      {error && (
        <div role="alert" className="card border-danger p-4 mb-6 text-sm text-danger">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="card flex flex-col gap-5 p-6">
        <div>
          <label htmlFor="case-name" className="block text-xs uppercase tracking-wider text-ivory-muted mb-1.5">
            Case Name *
          </label>
          <input
            id="case-name"
            type="text"
            required
            minLength={3}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. State of Maharashtra v. XYZ"
            className="w-full rounded-md border border-gold-line bg-surface-raised px-3.5 py-2.5 text-sm text-ivory placeholder:text-ivory-faint focus:border-gold focus:outline-none"
          />
        </div>

        <div>
          <label htmlFor="case-court" className="block text-xs uppercase tracking-wider text-ivory-muted mb-1.5">
            Court (optional)
          </label>
          <input
            id="case-court"
            type="text"
            value={court}
            onChange={(e) => setCourt(e.target.value)}
            placeholder="e.g. Supreme Court of India or Delhi High Court"
            className="w-full rounded-md border border-gold-line bg-surface-raised px-3.5 py-2.5 text-sm text-ivory placeholder:text-ivory-faint focus:border-gold focus:outline-none"
          />
        </div>

        <div>
          <label htmlFor="case-category" className="block text-xs uppercase tracking-wider text-ivory-muted mb-1.5">
            Category
          </label>
          <select
            id="case-category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full rounded-md border border-gold-line bg-surface-raised px-3.5 py-2.5 text-sm text-ivory focus:border-gold focus:outline-none"
          >
            {CATEGORIES.map((cat) => (
              <option key={cat} value={cat} className="bg-surface text-ivory">
                {cat}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="case-status" className="block text-xs uppercase tracking-wider text-ivory-muted mb-1.5">
            Case Status
          </label>
          <select
            id="case-status"
            value={status}
            onChange={(e) => setStatus(e.target.value as "decided" | "ongoing")}
            className="w-full rounded-md border border-gold-line bg-surface-raised px-3.5 py-2.5 text-sm text-ivory focus:border-gold focus:outline-none"
          >
            <option value="decided" className="bg-surface text-ivory">
              Decided (Judgment delivered)
            </option>
            <option value="ongoing" className="bg-surface text-ivory">
              Ongoing (Under trial / hearing)
            </option>
          </select>
          <p className="mt-1 text-xs text-ivory-muted">
            Note: Public polls and comments will only open if case status is Decided and Published.
          </p>
        </div>

        <div className="pt-2">
          <button
            type="submit"
            disabled={busy || name.trim().length < 3}
            className="w-full rounded-md bg-gold py-2.5 text-sm font-semibold text-ink transition-colors hover:bg-bronze disabled:opacity-40"
          >
            {busy ? "Starting Ingestion…" : "Start Case Ingestion"}
          </button>
        </div>
      </form>
    </div>
  );
}
