"use client";

import { useEffect, useRef, useState } from "react";
import { animate, createScope } from "animejs";

interface CounterItem {
  label: string;
  sublabel: string;
  targetValue: number;
  suffix?: string;
}

const METRICS: CounterItem[] = [
  {
    label: "Cases Analysed",
    sublabel: "Supreme Court & High Courts",
    targetValue: 8,
    suffix: "",
  },
  {
    label: "Judicial Quotes Verified",
    sublabel: "Verbatim quote anchored",
    targetValue: 148,
    suffix: "+",
  },
  {
    label: "Press Claims Fact-Checked",
    sublabel: "Audited against court findings",
    targetValue: 312,
    suffix: "",
  },
  {
    label: "Jan Mat Impressions",
    sublabel: "Public ballot engagements",
    targetValue: 4250,
    suffix: "+",
  },
];

export function MetricsCounters() {
  const rootRef = useRef<HTMLDivElement>(null);
  const scopeRef = useRef<ReturnType<typeof createScope> | null>(null);
  const [counts, setCounts] = useState<number[]>(() => METRICS.map(() => 0));

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

      if (reduceMotion) {
        setCounts(METRICS.map((m) => m.targetValue));
        return;
      }

      // Smooth count-up animation object
      const animState = {
        c0: 0,
        c1: 0,
        c2: 0,
        c3: 0,
      };

      animate(animState, {
        c0: METRICS[0].targetValue,
        c1: METRICS[1].targetValue,
        c2: METRICS[2].targetValue,
        c3: METRICS[3].targetValue,
        duration: 1800,
        ease: "outExpo",
        onUpdate: () => {
          setCounts([
            Math.round(animState.c0),
            Math.round(animState.c1),
            Math.round(animState.c2),
            Math.round(animState.c3),
          ]);
        },
      });
    });

    return () => {
      scopeRef.current?.revert();
    };
  }, []);

  return (
    <section
      ref={rootRef}
      className="card p-6 sm:p-8 bg-surface border-gold-line shadow-sm"
      aria-label="Platform Analysis Metrics"
    >
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 lg:gap-8 divide-y sm:divide-y-0 sm:divide-x divide-gold-line/40">
        {METRICS.map((metric, i) => (
          <div key={metric.label} className={`flex flex-col gap-1.5 ${i > 0 ? "pt-4 sm:pt-0 sm:pl-6" : ""}`}>
            <p className="eyebrow text-gold text-[10px] tracking-widest">{metric.label}</p>
            <p className="font-serif text-3xl sm:text-4xl font-bold text-ivory">
              {counts[i].toLocaleString()}
              <span className="text-gold text-2xl ml-0.5">{metric.suffix}</span>
            </p>
            <p className="text-xs text-ivory-faint">{metric.sublabel}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
