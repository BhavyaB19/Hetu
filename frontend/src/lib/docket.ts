import type { ListingView } from "@/lib/api";

/** The Supreme Court's e-pass portal for visitors (SuSwagatam). */
export const EPASS_URL = "https://suswagatam.sci.gov.in/";

const DAY = new Intl.DateTimeFormat("en-IN", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" });
const SHORT = new Intl.DateTimeFormat("en-IN", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" });
const CHECKED = new Intl.DateTimeFormat("en-IN", {
  day: "numeric",
  month: "short",
  hour: "numeric",
  minute: "2-digit",
  timeZone: "Asia/Kolkata",
});

/** Listing dates are calendar dates; format them without shifting by the viewer's timezone. */
export const longDay = (iso: string) => DAY.format(new Date(`${iso}T00:00:00Z`));
export const shortDay = (iso: string) => SHORT.format(new Date(`${iso}T00:00:00Z`));
export const checkedAt = (iso: string) => `${CHECKED.format(new Date(iso))} IST`;

export function benchLabel(size: number): string | null {
  if (size >= 5) return `Constitution or larger bench · ${size} judges`;
  if (size === 3) return "Three-judge bench";
  return null;
}

/** Listings grouped by courtroom, keeping the court's own order. */
export function byCourt(listings: ListingView[]): { court: string; first: ListingView; items: ListingView[] }[] {
  const groups = new Map<string, ListingView[]>();
  for (const l of listings) {
    const key = l.court ?? "Courtroom to be assigned";
    groups.set(key, [...(groups.get(key) ?? []), l]);
  }
  return [...groups].map(([court, items]) => ({ court, first: items[0], items }));
}

export function parties(l: ListingView): string {
  return l.respondent ? `${l.petitioner} v. ${l.respondent}` : l.petitioner;
}
