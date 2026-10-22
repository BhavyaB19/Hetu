#!/usr/bin/env node
/**
 * Turn a video into a scroll-scrubbed frame sequence for <ScrollSequence>.
 *
 *   node scripts/make-sequence.mjs <video> <name> [--fps 30] [--width 1600] [--mobile-width 800]
 *
 * Writes public/media/<name>/{0001.webp, ..., manifest.json} plus a smaller set under
 * public/media/<name>/mobile/. Needs ffmpeg on PATH. Examples:
 *
 *   node scripts/make-sequence.mjs lady-reveal.mp4 lady/reveal
 *   node scripts/make-sequence.mjs scales-balanced.mp4 scales/balanced --fps 24
 */
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";

const [video, name, ...rest] = process.argv.slice(2);
if (!video || !name) {
  console.error("Usage: node scripts/make-sequence.mjs <video> <name> [--fps 30] [--width 1600] [--mobile-width 800]");
  process.exit(1);
}
if (!existsSync(video)) {
  console.error(`Video not found: ${video}`);
  process.exit(1);
}
try {
  execFileSync("ffmpeg", ["-version"], { stdio: "ignore" });
} catch {
  console.error("ffmpeg is not installed or not on PATH. On Windows: winget install Gyan.FFmpeg (then open a new terminal).");
  process.exit(1);
}
const option = (flag, fallback) => {
  const i = rest.indexOf(flag);
  return i >= 0 ? Number(rest[i + 1]) : fallback;
};
const fps = option("--fps", 30);
const width = option("--width", 1600);
const mobileWidth = option("--mobile-width", 800);
const PAD = 4;

function extract(outDir, w) {
  rmSync(outDir, { recursive: true, force: true });
  mkdirSync(outDir, { recursive: true });
  execFileSync(
    "ffmpeg",
    ["-loglevel", "error", "-i", video, "-vf", `fps=${fps},scale='min(${w},iw)':-2`, "-c:v", "libwebp", "-quality", "72", join(outDir, `%0${PAD}d.webp`)],
    { stdio: "inherit" },
  );
  const count = readdirSync(outDir).filter((f) => f.endsWith(".webp")).length;
  const size = execFileSync("ffprobe", [
    "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", join(outDir, "0001.webp"),
  ]).toString().trim().split(",").map(Number);
  return { count, width: size[0], height: size[1] };
}

const outDir = join("public", "media", name);
const mobileDir = join(outDir, "mobile");
// The output folder is emptied first, so the source video must live somewhere else.
if (resolve(video).toLowerCase().startsWith(resolve(outDir).toLowerCase())) {
  console.error(`Move the video out of ${outDir} first: that folder is cleared before the frames are written.`);
  process.exit(1);
}
const desktop = extract(outDir, width);
const mobile = extract(mobileDir, mobileWidth);

const manifest = {
  count: Math.min(desktop.count, mobile.count),
  width: desktop.width,
  height: desktop.height,
  pattern: `/media/${name}/{n}.webp`,
  pad: PAD,
  mobile: { width: mobile.width, height: mobile.height, pattern: `/media/${name}/mobile/{n}.webp`, pad: PAD },
};
writeFileSync(join(outDir, "manifest.json"), JSON.stringify(manifest, null, 2));
console.log(`Wrote ${manifest.count} frames to ${outDir}`);
