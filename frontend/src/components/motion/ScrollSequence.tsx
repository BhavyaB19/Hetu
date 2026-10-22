"use client";

import { createScope, onScroll } from "animejs";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { forScreen, frameUrl, type SequenceManifest } from "@/lib/sequence";

export type SequenceStep = { at: number; text: string };

type Props = {
  /** Read on the server with `readSequence()`; the page renders its fallback when that is null. */
  manifest: SequenceManifest;
  /** Accessible description of what the sequence shows. */
  label: string;
  /** Scroll distance the sequence plays over, in viewport heights. */
  runwayVh?: number;
  /** Captions shown from a scroll progress (0 to 1) onwards; the last one is the end state. */
  steps?: SequenceStep[];
  /** Looping video shown before scrolling starts; its first frame should match frame 0. */
  idleVideo?: { mp4: string; webm?: string };
  /**
   * Layers drawn over the footage. Scroll progress is exposed to them as the CSS custom
   * property `--seq` (0 to 1), so they animate with `calc()` and no React renders.
   */
  stage?: ReactNode;
  /** Rendered over the bottom of the stage while it scrolls, e.g. a scroll cue. Not shown under reduced motion. */
  children?: ReactNode;
};

/**
 * Video frames scrubbed by scroll: the page scrolls normally, a sticky stage holds a
 * canvas, and scroll progress picks the frame. Plays forward on scroll down and in
 * reverse on scroll up. Frames come from a video (see scripts/make-sequence.mjs)
 * because seeking a compressed video backwards stutters, especially on iOS.
 */
export function ScrollSequence({ manifest: source, label, runwayVh = 300, steps = [], idleVideo, stage, children }: Props) {
  const rootRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [manifest, setManifest] = useState<SequenceManifest | null>(null);
  const [reduceMotion, setReduceMotion] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    setManifest(forScreen(source, window.innerWidth < 768));
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduceMotion(query.matches);
    const onChange = () => setReduceMotion(query.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, [source]);

  useEffect(() => {
    const root = rootRef.current;
    const canvas = canvasRef.current;
    if (!manifest || reduceMotion || !root || !canvas) return;

    const frames: (ImageBitmap | null)[] = new Array(manifest.count).fill(null);
    let current = 0;
    let stopped = false;

    const draw = () => {
      // Nearest loaded frame, so a slow connection shows a close frame instead of nothing.
      let bitmap: ImageBitmap | null = null;
      for (let d = 0; d < manifest.count && !bitmap; d++) {
        bitmap = frames[current - d] ?? frames[current + d] ?? null;
      }
      const ctx = canvas.getContext("2d");
      if (!bitmap || !ctx) return;
      const { width, height } = canvas;
      // Cover the stage, cropping the overflow evenly.
      const scale = Math.max(width / bitmap.width, height / bitmap.height);
      const w = bitmap.width * scale;
      const h = bitmap.height * scale;
      ctx.clearRect(0, 0, width, height);
      ctx.drawImage(bitmap, (width - w) / 2, (height - h) / 2, w, h);
    };

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(canvas.clientWidth * dpr);
      canvas.height = Math.round(canvas.clientHeight * dpr);
      draw();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);

    // First and last frame, then every 8th, then the rest: scrubbing works early and sharpens as it loads.
    const order = [0, manifest.count - 1];
    for (const step of [8, 4, 2, 1]) {
      for (let i = 0; i < manifest.count; i += step) if (!order.includes(i)) order.push(i);
    }
    const load = async () => {
      while (order.length && !stopped) {
        const i = order.shift()!;
        try {
          const res = await fetch(frameUrl(manifest, i));
          if (!res.ok) continue;
          frames[i] = await createImageBitmap(await res.blob());
          if (Math.abs(i - current) < 8) draw();
        } catch {
          // A missing frame is covered by its neighbours.
        }
      }
    };
    void Promise.all([load(), load(), load(), load()]);

    const scope = createScope({ root }).add(() => {
      onScroll({
        target: root,
        enter: "top top",
        leave: "bottom bottom",
        onUpdate: (self) => {
          const p = Math.min(1, Math.max(0, self.progress));
          root.style.setProperty("--seq", p.toFixed(4));
          const next = Math.round(p * (manifest.count - 1));
          // Captions only need whole-percent steps; avoids a React render per scroll event.
          setProgress(Math.round(p * 100) / 100);
          if (next !== current) {
            current = next;
            draw();
          }
        },
      });
    });

    return () => {
      stopped = true;
      observer.disconnect();
      scope.revert();
      frames.forEach((f) => f?.close());
    };
  }, [manifest, reduceMotion]);

  // The idle loop plays only at the top of the runway and never while the tab is hidden.
  const idle = progress < 0.02;
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const sync = () => {
      if (idle && !document.hidden) void video.play().catch(() => {});
      else video.pause();
    };
    sync();
    document.addEventListener("visibilitychange", sync);
    return () => document.removeEventListener("visibilitychange", sync);
  }, [idle]);

  const caption = [...steps].reverse().find((s) => (reduceMotion ? 1 : progress) >= s.at)?.text;

  const captionPlate = (
    <p
      aria-live="polite"
      className={`relative mt-auto mb-24 border border-gold-line bg-ink px-6 py-3 text-center font-serif text-2xl text-ivory transition-opacity duration-500 sm:px-9 sm:text-4xl ${caption ? "opacity-100" : "opacity-0"}`}
    >
      {caption}
    </p>
  );

  // Reduced motion: the end state as a still, no runway and no loop; layers stay at their start.
  if (reduceMotion && manifest) {
    return (
      <section aria-label={label} className="relative" style={{ ["--seq" as string]: 0 }}>
        <div className="relative flex h-[calc(100svh-5rem)] min-h-[32rem] flex-col items-center justify-center overflow-hidden">
          {/* eslint-disable-next-line @next/next/no-img-element -- frames are plain static files */}
          <img
            src={frameUrl(manifest, manifest.count - 1)}
            alt={label}
            width={manifest.width}
            height={manifest.height}
            className="absolute inset-0 h-full w-full object-cover"
          />
          {stage}
          {captionPlate}
        </div>
      </section>
    );
  }

  return (
    <section
      ref={rootRef}
      aria-label={label}
      className="relative"
      style={{ height: `${runwayVh}vh`, ["--seq" as string]: 0 }}
    >
      {/* Pinned below the sticky site header (h-20) so the top of the frame is never covered. */}
      <div className="sticky top-20 flex h-[calc(100svh-5rem)] min-h-[32rem] flex-col items-center justify-center overflow-hidden">
        <canvas ref={canvasRef} role="img" aria-label={label} className="absolute inset-0 h-full w-full" />
        {idleVideo && (
          <video
            ref={videoRef}
            muted
            loop
            playsInline
            preload="metadata"
            aria-hidden="true"
            className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-300 ${idle ? "opacity-100" : "opacity-0"}`}
          >
            {idleVideo.webm && <source src={idleVideo.webm} type="video/webm" />}
            <source src={idleVideo.mp4} type="video/mp4" />
          </video>
        )}
        {stage}
        {captionPlate}
        <div className="relative mb-8">{children}</div>
      </div>
    </section>
  );
}
