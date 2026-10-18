import React from "react";

export function DisclaimerBanner() {
  return (
    <div
      role="note"
      className="border-b border-gold-line bg-gold-soft px-4 py-2 text-center text-xs text-ivory-muted"
    >
      <span className="font-semibold text-gold mr-1.5 uppercase tracking-wider text-[10px]">Notice:</span>
      Research &amp; education platform. Not legal advice or an outcome predictor. Public sentiment is not representative of all of India.
    </div>
  );
}
