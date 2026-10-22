import type { CaseView } from "@/lib/api";

/** Below this many media claims the tilt is scaled down, so one claim cannot swing the scales. */
const MIN_CLAIMS = 5;
export const MAX_TILT_DEG = 14;

export type BalanceVariant = "media-heavy" | "media-leaning" | "balanced" | "court-leaning" | "court-heavy";

export type Balance = {
  claims: number;
  /** Media claims the judgment contradicts or does not support. */
  unsupported: number;
  events: number;
  /** Timeline events the court relied on that no article mentioned. */
  unreported: number;
  /** -1 (court side heavier) to 1 (media side heavier). */
  lean: number;
  variant: BalanceVariant;
};

/**
 * How the coverage weighs against the judgment. The media pan gets heavier when the press
 * reports things the court did not find; the court pan gets heavier when the court relied
 * on events the press left out. Null when there is no coverage to weigh.
 */
export function coverageBalance(view: CaseView): Balance | null {
  const claims = view.media.flatMap((m) => m.claims);
  if (!view.judgment || view.media.length === 0) return null;

  const unsupported = claims.filter((c) => c.verdict !== "supported").length;
  const overreach = claims.length ? unsupported / claims.length : 0;

  const totalWeight = view.timeline.reduce((sum, e) => sum + e.court_weight, 0);
  const missed = view.timeline.filter((e) => e.media_weight === 0);
  const underreported = totalWeight ? missed.reduce((sum, e) => sum + e.court_weight, 0) / totalWeight : 0;

  const confidence = Math.min(1, claims.length / MIN_CLAIMS);
  const lean = (overreach - underreported) * confidence;
  const size = Math.abs(lean);
  const side = lean > 0 ? "media" : "court";
  const variant: BalanceVariant = size < 0.15 ? "balanced" : size < 0.45 ? `${side}-leaning` : `${side}-heavy`;

  return { claims: claims.length, unsupported, events: view.timeline.length, unreported: missed.length, lean, variant };
}

export const VARIANT_LABEL: Record<BalanceVariant, string> = {
  "media-heavy": "Coverage carries much that the judgment does not support",
  "media-leaning": "Coverage carries some claims the judgment does not support",
  balanced: "Coverage and judgment are broadly in balance",
  "court-leaning": "Coverage left out some events the court relied on",
  "court-heavy": "Coverage left out much of what the court relied on",
};
