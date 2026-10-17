export const SENTIMENT = {
  support_victim: { label: "Support victim", color: "var(--color-viz-1)" },
  support_accused: { label: "Support accused", color: "var(--color-viz-2)" },
  neutral_uncertain: { label: "Neutral / uncertain", color: "var(--color-viz-3)" },
  against_media_bias: { label: "Against media bias", color: "var(--color-viz-4)" },
} as const;

export const FRAMING: Record<string, string> = {
  sensational: "Sensational",
  procedural: "Procedural",
  victim_centric: "Victim-centric",
  accused_centric: "Accused-centric",
  other: "Other",
};

export const VERDICT = {
  supported: { label: "Supported", icon: "✓", className: "text-ok" },
  contradicted: { label: "Contradicted", icon: "✕", className: "text-danger" },
  absent: { label: "Not in judgment", icon: "?", className: "text-ivory-muted" },
} as const;

export function pct(share: number): string {
  return `${Math.round(share * 100)}%`;
}

export function date(value: string | null | undefined): string {
  if (!value) return "Undated";
  return new Date(`${value}T00:00:00`).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function tone(value: number): string {
  const word =
    value <= -0.6 ? "alarmed" : value <= -0.2 ? "negative" : value < 0.2 ? "neutral" : value < 0.6 ? "positive" : "celebratory";
  return `${value > 0 ? "+" : ""}${value.toFixed(1)} (${word})`;
}
