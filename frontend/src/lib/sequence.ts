/** Frame sequences extracted from a video by `scripts/make-sequence.mjs`. */
export type SequenceManifest = {
  count: number;
  width: number;
  height: number;
  /** Frame URL with `{n}` for the zero-padded frame number, starting at 1. */
  pattern: string;
  pad: number;
  /** Smaller frames for narrow screens, same frame count. */
  mobile?: Omit<SequenceManifest, "mobile" | "count">;
};

export function frameUrl(m: SequenceManifest, index: number): string {
  return m.pattern.replace("{n}", String(index + 1).padStart(m.pad, "0"));
}

/** The frame set for this screen width. */
export function forScreen(m: SequenceManifest, narrow: boolean): SequenceManifest {
  return narrow && m.mobile ? { ...m, ...m.mobile } : m;
}
