import Link from "next/link";

import { API_URL, api } from "@/lib/api";

export const dynamic = "force-dynamic";

const STORIES = [
  ["The Court's Story", "What the judgment establishes: facts, motive, trigger, escalation and reasoning."],
  ["The Media's Story", "How outlets framed it, and whether their factual claims match the judgment."],
  ["The Public's Story", "How people reacted: overall stance and recurring themes, never individuals."],
];

export default async function Home() {
  const { data: cases, error } = await api.GET("/cases").catch(() => ({ data: undefined, error: true }));

  return (
    <div className="flex flex-col gap-14 pt-8">
      <section className="flex flex-col items-center gap-6 text-center">
        <p className="eyebrow">Perception Gap Research</p>
        <h1 className="max-w-3xl font-serif text-4xl leading-tight text-ivory sm:text-6xl">
          One verdict. Three stories. One connected view.
        </h1>
        <p className="max-w-xl text-ivory-muted">
          Hetu connects a court judgment with its news coverage and public reaction, and measures how far the
          narratives drift from what the court found.
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        {STORIES.map(([title, body], i) => (
          <article key={title} className="card p-6">
            <p className="eyebrow mb-3">0{i + 1}</p>
            <h2 className="mb-2 font-serif text-xl text-ivory">{title}</h2>
            <p className="text-sm text-ivory-muted">{body}</p>
          </article>
        ))}
      </section>

      <hr className="gold-rule" />

      <section className="flex flex-col gap-4">
        <h2 className="font-serif text-2xl text-ivory">Cases</h2>
        {error || !cases ? (
          <p className="card p-6 text-sm text-ivory-muted">
            Can&apos;t reach the Hetu API at {API_URL}. Start the backend and refresh.
          </p>
        ) : cases.length === 0 ? (
          <p className="card p-6 text-sm text-ivory-muted">
            No published cases yet. An admin must publish a case or load the demo with <code className="text-gold">python -m app.cli load fixtures/jan-mat-v-state.json</code>.
          </p>
        ) : (
          <ul className="grid gap-4 md:grid-cols-2">
            {cases.map((c) => (
              <li key={c.slug}>
                <Link
                  href={`/cases/${c.slug}`}
                  className="card flex h-full items-start justify-between gap-6 p-6 transition-colors hover:border-gold"
                >
                  <div className="flex flex-col gap-2">
                    <p className="text-xs text-ivory-muted">
                      {c.category}
                      {c.is_illustrative && <span className="ml-2 text-gold">Illustrative demo</span>}
                    </p>
                    <h3 className="font-serif text-2xl text-ivory">{c.title}</h3>
                    {c.summary && <p className="text-sm leading-relaxed text-ivory-muted">{c.summary}</p>}
                  </div>
                  {c.gap_score !== null && (
                    <div className="shrink-0 text-right">
                      <p className="text-3xl font-semibold text-gold">{Math.round(c.gap_score)}</p>
                      <p className="text-[10px] uppercase tracking-widest text-ivory-faint">Gap index</p>
                    </div>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
