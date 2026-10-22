/** The site's standing notice, set like a newspaper's dateline above a double rule. */
export function DisclaimerBanner() {
  return (
    <div
      role="note"
      className="press-rule flex min-h-9 items-center justify-center gap-3 bg-ink px-4 py-2 text-center text-[11px] uppercase tracking-[0.22em] text-ivory-faint"
    >
      <span className="font-semibold text-gold">Notice</span>
      <span>
        Independent research on how verdicts are reported and received · Not a court · No predictions · No polls on
        pending trials
      </span>
    </div>
  );
}
