import { EvidenceLink } from "@/components/EvidenceLink";
import type { JudgmentView, MediaView } from "@/lib/api";
import { VERDICT, pct } from "@/lib/format";

const FINDINGS = [
  ["facts", "Facts"],
  ["motive", "Motive"],
  ["trigger", "Trigger"],
  ["court_reasoning", "Reasoning"],
  ["outcome", "Outcome"],
] as const;

type Verdict = keyof typeof VERDICT;
const ORDER: Verdict[] = ["contradicted", "absent", "supported"];

/** What the court established, next to the factual claims media made, each checked against it. */
export function CourtVsMedia({ judgment, media }: { judgment: JudgmentView; media: MediaView[] }) {
  const claims = media
    .flatMap((article) => article.claims.map((claim) => ({ ...claim, outlet: article.outlet })))
    .sort((a, b) => ORDER.indexOf(a.verdict) - ORDER.indexOf(b.verdict));
  const counts = ORDER.map((v) => ({ verdict: v, count: claims.filter((c) => c.verdict === v).length }));

  return (
    <div className="grid items-start gap-4 lg:grid-cols-2">
      <div className="card flex flex-col gap-4 p-6 lg:sticky lg:top-6">
        <h3 className="font-serif text-xl text-ivory">What the court found</h3>
        <dl className="flex flex-col gap-4">
          {FINDINGS.map(([key, label]) => (
            <div key={key}>
              <dt className="text-xs uppercase tracking-widest text-ivory-faint">{label}</dt>
              <dd className="mt-1 text-sm leading-relaxed text-ivory">{judgment[key]}</dd>
              <dd className="mt-1">
                <EvidenceLink evidence={judgment.evidence[key]} />
              </dd>
            </div>
          ))}
        </dl>
        <div className="flex flex-wrap gap-2">
          {judgment.legal_provisions.map((p) => (
            <span key={p} className="rounded-full border border-gold-line px-3 py-1 text-xs text-ivory-muted">
              {p}
            </span>
          ))}
        </div>
      </div>

      <div className="card flex flex-col gap-4 p-6">
        <h3 className="font-serif text-xl text-ivory">What the media claimed</h3>
        <div>
          <div className="flex h-3 gap-0.5 overflow-hidden rounded" role="img" aria-label="Media claims by verdict">
            {counts.map(
              ({ verdict, count }) =>
                count > 0 && (
                  <div
                    key={verdict}
                    title={`${VERDICT[verdict].label}: ${count}`}
                    style={{
                      flexGrow: count,
                      background:
                        verdict === "contradicted" ? "var(--color-danger)" : verdict === "supported" ? "var(--color-ok)" : "var(--color-ivory-faint)",
                    }}
                  />
                ),
            )}
          </div>
          <p className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ivory-muted">
            {counts.map(({ verdict, count }) => (
              <span key={verdict}>
                <span className={VERDICT[verdict].className}>{VERDICT[verdict].icon}</span> {VERDICT[verdict].label}:{" "}
                {count} ({pct(claims.length ? count / claims.length : 0)})
              </span>
            ))}
          </p>
        </div>
        <ul className="flex flex-col divide-y divide-gold-line">
          {claims.map((claim, i) => (
            <li key={i} className="flex flex-col gap-1.5 py-3">
              <p className="text-sm text-ivory">
                <span className={`mr-2 font-semibold ${VERDICT[claim.verdict].className}`}>
                  {VERDICT[claim.verdict].icon} {VERDICT[claim.verdict].label}
                </span>
                {claim.text}
              </p>
              <p className="text-xs leading-relaxed text-ivory-muted">{claim.rationale}</p>
              <div className="flex flex-wrap gap-4">
                <EvidenceLink evidence={claim.evidence} label={claim.outlet} />
                <EvidenceLink evidence={claim.judgment_evidence} label="Judgment" />
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
