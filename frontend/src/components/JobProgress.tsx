"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import type { JobView } from "@/lib/api";

const STEPS = [
  { key: "collecting", label: "Collecting sources", detail: "TinyFish agents read the judgment, coverage and comments" },
  { key: "analysing", label: "Analysing", detail: "Extracting evidence, removing personal details, scoring" },
  { key: "done", label: "Ready", detail: "Opening the dashboard" },
] as const;

const POLL_MS = 2000;

function elapsed(from: string): string {
  const s = Math.max(0, Math.round((Date.now() - new Date(from).getTime()) / 1000));
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`;
}

/** Polls a case job and shows each stage and the agents' live log. */
export function JobProgress({ initial }: { initial: JobView }) {
  const router = useRouter();
  const [job, setJob] = useState(initial);
  const [, tick] = useState(0);
  const logEnd = useRef<HTMLLIElement>(null);

  useEffect(() => {
    if (job.status === "done" || job.status === "failed") return;
    const timer = setInterval(async () => {
      try {
        const res = await fetch(`/api/jobs/${job.id}`, { cache: "no-store" });
        if (res.ok) setJob(await res.json());
      } catch {
        // Keep polling; a dropped request is not a failed job.
      }
      tick((n) => n + 1);
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [job.id, job.status]);

  useEffect(() => {
    if (job.status === "done" && job.slug) {
      const t = setTimeout(() => router.push(`/cases/${job.slug}`), 1500);
      return () => clearTimeout(t);
    }
  }, [job.status, job.slug, router]);

  useEffect(() => {
    logEnd.current?.scrollIntoView({ block: "nearest" });
  }, [job.events.length]);

  // Index of the step that is running, or that failed (analysis fails after "Sources collected").
  const reached =
    job.status === "failed"
      ? job.events.some((e) => e.message.startsWith("Sources collected")) ? 1 : 0
      : STEPS.findIndex((s) => s.key === job.status);
  const stateOf = (i: number) =>
    job.status === "done" || i < reached ? "complete" : i > reached ? "pending" : job.status === "failed" ? "failed" : "active";
  const started = job.events[0]?.at;

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-2">
        <p className="eyebrow">Analysing case</p>
        <h1 className="font-serif text-3xl text-ivory sm:text-4xl">{job.name}</h1>
        {started && job.status !== "done" && job.status !== "failed" && (
          <p className="text-sm text-ivory-muted">Running for {elapsed(started)}</p>
        )}
      </header>

      <ol className="grid gap-3 sm:grid-cols-3">
        {STEPS.map((step, i) => {
          const state = stateOf(i);
          const [failed, complete, active] = [state === "failed", state === "complete", state === "active"];
          return (
            <li
              key={step.key}
              className={`card flex gap-3 p-4 ${active ? "border-gold" : ""} ${failed ? "border-danger" : ""}`}
              aria-current={active ? "step" : undefined}
            >
              <span
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-sm ${
                  failed ? "border-danger text-danger" : complete ? "border-gold bg-gold text-ink" : "border-gold-line text-ivory-muted"
                } ${active ? "animate-pulse border-gold text-gold" : ""}`}
              >
                {failed ? "✕" : complete ? "✓" : i + 1}
              </span>
              <div>
                <p className="text-sm text-ivory">{step.label}</p>
                <p className="mt-0.5 text-xs text-ivory-muted">{step.detail}</p>
              </div>
            </li>
          );
        })}
      </ol>

      {job.status === "failed" && (
        <div role="alert" className="card border-danger p-5 text-sm">
          <p className="text-danger">The case could not be completed.</p>
          <p className="mt-1 text-ivory-muted">{job.error}</p>
          <Link href="/" className="mt-3 inline-block text-gold hover:text-bronze">
            ← Try another case
          </Link>
        </div>
      )}
      {job.status === "done" && job.slug && (
        <Link href={`/cases/${job.slug}`} className="w-fit rounded-md bg-gold px-5 py-2 text-sm font-semibold text-ink hover:bg-bronze">
          Open the dashboard →
        </Link>
      )}

      <section className="card p-5">
        <h2 className="mb-3 text-xs uppercase tracking-widest text-ivory-faint">Agent log</h2>
        <ol className="flex max-h-96 flex-col gap-1.5 overflow-y-auto font-mono text-xs" aria-live="polite">
          {job.events.map((e, i) => (
            <li key={i} className="flex gap-3">
              <span className="shrink-0 text-ivory-faint">
                {new Date(e.at).toLocaleTimeString("en-IN", { hour12: false })}
              </span>
              <span className={e.level === "error" ? "text-danger" : e.level === "warning" ? "text-gold" : "text-ivory-muted"}>
                {e.message}
              </span>
            </li>
          ))}
          <li ref={logEnd} />
        </ol>
      </section>
    </div>
  );
}
