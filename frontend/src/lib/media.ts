// Server components only: reads the public folder from disk.
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import type { SequenceManifest } from "@/lib/sequence";

/**
 * The Lady Justice and scales footage is added to public/media/ separately (see
 * scripts/make-sequence.mjs). Checking on the server means pages render their fallback
 * art when it is missing, without the browser requesting files that are not there.
 */
const PUBLIC = join(process.cwd(), "public");

export function hasMedia(url: string): boolean {
  return existsSync(join(PUBLIC, url));
}

export function readSequence(name: string): SequenceManifest | null {
  try {
    const m = JSON.parse(readFileSync(join(PUBLIC, "media", name, "manifest.json"), "utf-8")) as SequenceManifest;
    return m.count > 0 && m.pattern ? m : null;
  } catch {
    return null;
  }
}
