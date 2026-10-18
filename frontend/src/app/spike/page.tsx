"use client";

import { useEffect, useRef, useState } from "react";
import { notFound } from "next/navigation";
import {
  animate,
  createTimeline,
  createDrawable,
  onScroll,
  spring,
  createScope,
} from "animejs";

export default function SpikePage() {
  if (process.env.NODE_ENV === "production") {
    notFound();
  }

  const rootRef = useRef<HTMLDivElement>(null);
  const scopeRef = useRef<ReturnType<typeof createScope> | null>(null);
  const [springVal, setSpringVal] = useState<number>(0);
  const [timelineStatus, setTimelineStatus] = useState<string>("initializing");
  const [isReducedMotion, setIsReducedMotion] = useState<boolean>(false);
  const [cleanupCount, setCleanupCount] = useState<number>(0);

  useEffect(() => {
    if (!rootRef.current) return;

    scopeRef.current = createScope({
      root: rootRef.current,
      mediaQueries: {
        reduceMotion: "(prefers-reduced-motion: reduce)",
      },
    }).add((self) => {
      if (!self) return;
      const { reduceMotion } = self.matches;
      setIsReducedMotion(!!reduceMotion);

      // Proof 1: createTimeline sequence
      const tl = createTimeline({
        defaults: { duration: 400, ease: "inOutQuad" },
        onBegin: () => setTimelineStatus("running"),
        onComplete: () => setTimelineStatus("completed"),
      });

      tl.add(".spike-tl-step-1", { translateX: [0, 80], opacity: [0.2, 1] })
        .add(".spike-tl-step-2", { translateX: [0, 80], opacity: [0.2, 1] }, "+=100")
        .add(".spike-tl-step-3", { scale: [1, 1.15], opacity: [0.2, 1] }, "+=100");

      // Proof 2: createDrawable + onScroll sync
      const [drawable] = createDrawable(".spike-draw-path");
      if (drawable) {
        animate(drawable, {
          draw: ["0 0", "0 1"],
          autoplay: onScroll({
            target: ".spike-scroll-target",
            sync: true,
            enter: "top 90%",
            leave: "bottom 10%",
          }),
        });
      }

      // Proof 3: spring-driven motion
      animate(".spike-spring-pan", {
        rotate: reduceMotion ? 12 : [-15, 15],
        duration: 1000,
        ease: spring({ bounce: 0.35, duration: 800 }),
        loop: !reduceMotion,
        alternate: true,
        onUpdate: (anim) => {
          // Track dynamic numerical value
          const rot = anim.targets[0] as HTMLElement;
          if (rot) {
            setSpringVal(Math.round(parseFloat(rot.style.transform?.replace(/[^\d.-]/g, "") || "0")));
          }
        },
      });
    });

    // Proof 4: StrictMode double-mount cleanup via scope.revert()
    return () => {
      setCleanupCount((prev) => prev + 1);
      scopeRef.current?.revert();
    };
  }, []);

  return (
    <div ref={rootRef} className="min-h-[220vh] p-8 max-w-4xl mx-auto flex flex-col gap-12 text-ivory">
      <header className="border-b border-gold-line pb-4">
        <p className="eyebrow">Throwaway Spike</p>
        <h1 className="font-serif text-3xl text-gold">Anime.js v4 API Verification Spike</h1>
        <p className="text-sm text-ivory-muted mt-1">
          Proves createTimeline, createDrawable + onScroll, spring(), createScope mediaQueries, and StrictMode cleanup.
        </p>
      </header>

      {/* Proof 1: Timeline */}
      <section className="card p-6 flex flex-col gap-4">
        <div className="flex justify-between items-center">
          <h2 className="font-serif text-xl">1. Timeline Sequence (createTimeline)</h2>
          <span className="text-xs px-2 py-1 rounded bg-gold/10 text-gold border border-gold/30">
            Status: {timelineStatus}
          </span>
        </div>
        <div className="flex gap-4 items-center pt-2">
          <div className="spike-tl-step-1 px-4 py-2 bg-track rounded border border-gold-line text-xs">Step 1</div>
          <div className="spike-tl-step-2 px-4 py-2 bg-track rounded border border-gold-line text-xs">Step 2</div>
          <div className="spike-tl-step-3 px-4 py-2 bg-gold text-ink font-semibold rounded text-xs">Step 3</div>
        </div>
      </section>

      {/* Proof 2: Spring Physics */}
      <section className="card p-6 flex flex-col gap-4">
        <div className="flex justify-between items-center">
          <h2 className="font-serif text-xl">2. Spring Physics (spring())</h2>
          <span className="text-xs text-ivory-muted">Tracked Angle: {springVal}°</span>
        </div>
        <div className="h-28 flex items-center justify-center bg-track/40 rounded border border-gold-line">
          <div
            className="spike-spring-pan w-48 h-2 bg-gold rounded relative origin-center"
            style={{ transformOrigin: "center center" }}
          >
            <div className="absolute -top-3 -left-3 w-6 h-6 rounded-full bg-viz-1" />
            <div className="absolute -top-3 -right-3 w-6 h-6 rounded-full bg-viz-2" />
          </div>
        </div>
      </section>

      {/* Proof 3: createScope & Reduced Motion */}
      <section className="card p-6 flex flex-col gap-4">
        <h2 className="font-serif text-xl">3. Scoping & React 19 StrictMode Cleanup (createScope)</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="p-3 bg-track rounded border border-gold-line">
            <span className="text-ivory-muted">Reduced Motion Active:</span>{" "}
            <span className={isReducedMotion ? "text-gold font-bold" : "text-ok"}>
              {isReducedMotion ? "YES (Loops Disabled)" : "NO (Full Motion)"}
            </span>
          </div>
          <div className="p-3 bg-track rounded border border-gold-line">
            <span className="text-ivory-muted">revert() Invoked:</span>{" "}
            <span className="text-ok font-mono">{cleanupCount} time(s)</span>
          </div>
        </div>
      </section>

      {/* Proof 4: createDrawable + onScroll */}
      <section className="spike-scroll-target card p-6 flex flex-col gap-4 mt-8">
        <h2 className="font-serif text-xl">4. SVG Stroke Drawing on Scroll (createDrawable + onScroll)</h2>
        <p className="text-xs text-ivory-muted">Scroll down to observe the SVG path draw continuously with scroll progress.</p>
        <div className="py-6 flex justify-center">
          <svg viewBox="0 0 400 120" className="w-full max-w-md h-28" stroke="#c08a3e" fill="none" strokeWidth="3">
            <path
              className="spike-draw-path"
              d="M 10 60 Q 100 0 200 60 T 390 60"
              strokeLinecap="round"
            />
          </svg>
        </div>
      </section>

      <div className="h-48 flex items-center justify-center text-xs text-ivory-faint">
        ↓ Scroll runway to drive onScroll sync ↓
      </div>
    </div>
  );
}
