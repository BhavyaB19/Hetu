import type { components } from "@/lib/api/schema";

type Verdict = components["schemas"]["ClaimView"]["verdict"];

export const MARK_LABEL: Record<Verdict, string> = {
  supported: "Supported by the judgment",
  absent: "Not in the judgment",
  contradicted: "Contradicted by the judgment",
};

/** One claim, one cell: filled holds, hollow is unsupported, struck is contradicted. */
export function ClaimMark({ verdict }: { verdict: Verdict }) {
  return (
    <span
      title={MARK_LABEL[verdict]}
      className={`relative inline-block h-3.5 w-3.5 rounded-full border-[1.5px] ${
        verdict === "supported" ? "border-gold bg-gold" : verdict === "absent" ? "border-gold" : "border-ivory-faint"
      }`}
    >
      {verdict === "contradicted" && (
        <span className="absolute -inset-x-1 top-1/2 h-[1.5px] -rotate-[35deg] bg-ivory-muted" aria-hidden />
      )}
    </span>
  );
}

export function ClaimMarks({ verdicts }: { verdicts: Verdict[] }) {
  const counts = verdicts.reduce<Record<string, number>>((acc, v) => ({ ...acc, [v]: (acc[v] ?? 0) + 1 }), {});
  const summary = (["supported", "absent", "contradicted"] as const)
    .filter((v) => counts[v])
    .map((v) => `${counts[v]} ${MARK_LABEL[v].toLowerCase()}`)
    .join(", ");
  return (
    <span className="flex gap-1.5" role="img" aria-label={summary}>
      {verdicts.map((v, i) => (
        <ClaimMark key={i} verdict={v} />
      ))}
    </span>
  );
}
