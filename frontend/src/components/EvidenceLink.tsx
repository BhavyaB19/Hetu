"use client";

import { useRef } from "react";

import type { Evidence } from "@/lib/api";
import { date } from "@/lib/format";

/** A small link that opens the exact source passage behind a finding. */
export function EvidenceLink({ evidence, label = "Source" }: { evidence?: Evidence | null; label?: string }) {
  const dialog = useRef<HTMLDialogElement>(null);
  if (!evidence) return null;

  return (
    <>
      <button
        type="button"
        onClick={() => dialog.current?.showModal()}
        className="inline-flex items-center gap-1 text-xs text-gold underline decoration-gold-line underline-offset-4 hover:text-bronze"
      >
        <span aria-hidden>§</span> {label}
      </button>
      <dialog
        ref={dialog}
        onClick={(e) => e.target === dialog.current && dialog.current?.close()}
        className="card m-auto w-[min(36rem,calc(100vw-2rem))] p-6 text-ivory"
      >
        <p className="eyebrow mb-3">Evidence</p>
        <blockquote className="border-l-2 border-gold pl-4 font-serif text-lg leading-relaxed">
          “{evidence.quote}”
        </blockquote>
        <p className="mt-4 text-sm text-ivory-muted">
          {evidence.source_name} · {date(evidence.published_at)}
        </p>
        <div className="mt-5 flex items-center justify-between gap-4">
          {evidence.url ? (
            <a href={evidence.url} target="_blank" rel="noreferrer" className="text-sm text-gold hover:text-bronze">
              Open original source ↗
            </a>
          ) : (
            <span className="text-xs text-ivory-faint">Illustrative source: no external link.</span>
          )}
          <button
            type="button"
            onClick={() => dialog.current?.close()}
            className="rounded-md border border-gold-line px-3 py-1.5 text-sm hover:border-gold"
          >
            Close
          </button>
        </div>
      </dialog>
    </>
  );
}
