import { ScrollSequence } from "@/components/motion/ScrollSequence";
import { BalanceScales } from "@/components/verdicts/BalanceScales";
import { VARIANT_LABEL, type Balance } from "@/lib/balance";
import { readSequence } from "@/lib/media";

/**
 * The scales weigh the coverage against the judgment. The rendered clip (one per
 * variant) zooms in on the scales; the vector scales stand in until it is added. The
 * numbers are always shown as text: the tilt is never the only signal.
 */
export function CoverageBalance({ balance }: { balance: Balance }) {
  const clip = readSequence(`scales/${balance.variant}`);
  return (
    <div className="flex flex-col gap-6">
      {clip ? (
        <ScrollSequence manifest={clip} label={`Scales of justice. ${VARIANT_LABEL[balance.variant]}.`} runwayVh={200} />
      ) : (
        <BalanceScales lean={balance.lean} />
      )}

      <p className="text-center font-serif text-xl text-ivory sm:text-2xl">{VARIANT_LABEL[balance.variant]}</p>

      <dl className="grid gap-3 sm:grid-cols-2">
        <div className="card p-4">
          <dt className="eyebrow">Media pan</dt>
          <dd className="mt-1 text-sm text-ivory-muted">
            <strong className="text-ivory">
              {balance.unsupported} of {balance.claims}
            </strong>{" "}
            media claims are not supported by the judgment.
          </dd>
        </div>
        <div className="card p-4">
          <dt className="eyebrow">Court pan</dt>
          <dd className="mt-1 text-sm text-ivory-muted">
            <strong className="text-ivory">
              {balance.unreported} of {balance.events}
            </strong>{" "}
            events in the court&apos;s timeline went unreported.
          </dd>
        </div>
      </dl>
      {balance.claims < 5 && (
        <p className="text-xs text-ivory-faint">Few media claims were found, so the tilt is reduced.</p>
      )}
    </div>
  );
}
