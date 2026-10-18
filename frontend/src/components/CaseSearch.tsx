"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

/** Starts collecting a case with the TinyFish agents, then opens its live progress page. */
export function CaseSearch() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [court, setCourt] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/cases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), court: court.trim() || null }),
      });
      const body = await res.json();
      if (!res.ok) {
        const detail = Array.isArray(body.detail) ? body.detail[0]?.msg : body.detail;
        throw new Error(detail ?? "Could not start the case.");
      }
      router.push(`/jobs/${body.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start the case.");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="w-full max-w-2xl text-left">
      <div className="card flex flex-col gap-2 p-2 sm:flex-row sm:items-center">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Case name, e.g. Manu Sharma v. State (NCT of Delhi)"
          aria-label="Case name"
          required
          minLength={3}
          className="min-w-0 flex-[2] bg-transparent px-3 py-2 text-sm text-ivory placeholder:text-ivory-faint focus:outline-none"
        />
        <input
          value={court}
          onChange={(e) => setCourt(e.target.value)}
          placeholder="Court (optional)"
          aria-label="Court"
          className="min-w-0 flex-1 border-gold-line bg-transparent px-3 py-2 text-sm text-ivory placeholder:text-ivory-faint focus:outline-none sm:border-l"
        />
        <button
          type="submit"
          disabled={busy || name.trim().length < 3}
          className="rounded-md bg-gold px-5 py-2 text-sm font-semibold text-ink transition-colors hover:bg-bronze disabled:opacity-40"
        >
          {busy ? "Starting…" : "Analyse"}
        </button>
      </div>
      {error ? (
        <p role="alert" className="mt-2 text-xs text-danger">
          {error}
        </p>
      ) : (
        <p className="mt-2 text-xs text-ivory-faint">
          Browser agents read the judgment, news coverage and public comments. Public pages only; takes a few minutes.
        </p>
      )}
    </form>
  );
}
