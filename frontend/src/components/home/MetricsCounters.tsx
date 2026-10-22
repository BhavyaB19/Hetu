"use client";

import { useEffect, useRef, useState } from "react";
import { animate, createScope } from "animejs";

import type { components } from "@/lib/api/schema";

type HomeCounters = components["schemas"]["HomeCounters"];

interface CounterItem {
  label: string;
  sublabel: string;
  value: number | null;
  decimals: number;
}

function metricsFrom(counters: HomeCounters): CounterItem[] {
  return [
    { label: "Cases Analysed", sublabel: "Published verdicts", value: counters.total_cases, decimals: 0 },
    { label: "Jan Mat Votes", sublabel: "Public ballot responses", value: counters.total_votes, decimals: 0 },
    { label: "Comments", sublabel: "Moderated public discussion", value: counters.total_comments, decimals: 0 },
    {
      label: "Average Perception Gap",
      sublabel: "Across published cases, out of 100",
      value: counters.avg_perception_gap,
      decimals: 1,
    },
  ];
}

const format = (value: number, decimals: number) =>
  value.toLocaleString("en-IN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });

/** Live platform counts from `GET /home`; counts up once on load. */
export function MetricsCounters({ counters }: { counters: HomeCounters }) {
  const rootRef = useRef<HTMLDivElement>(null);
  const metrics = metricsFrom(counters);
  const targets = metrics.map((m) => m.value ?? 0);
  const [counts, setCounts] = useState<number[]>(() => targets.map(() => 0));
  const targetKey = targets.join(",");

  useEffect(() => {
    if (!rootRef.current) return;
    const end = targetKey.split(",").map(Number);

    const scope = createScope({
      root: rootRef.current,
      mediaQueries: { reduceMotion: "(prefers-reduced-motion: reduce)" },
    }).add((self) => {
      if (!self) return;
      if (self.matches.reduceMotion) {
        setCounts(end);
        return;
      }
      const state = { progress: 0 };
      animate(state, {
        progress: 1,
        duration: 1800,
        ease: "outExpo",
        onUpdate: () => setCounts(end.map((v) => v * state.progress)),
      });
    });

    return () => scope.revert();
  }, [targetKey]);

  return (
    <section
      ref={rootRef}
      className="card p-6 sm:p-8 bg-surface border-gold-line shadow-sm"
      aria-label="Platform Analysis Metrics"
    >
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 lg:gap-8 divide-y sm:divide-y-0 sm:divide-x divide-gold-line/40">
        {metrics.map((metric, i) => (
          <div key={metric.label} className={`flex flex-col gap-1.5 ${i > 0 ? "pt-4 sm:pt-0 sm:pl-6" : ""}`}>
            <p className="eyebrow text-gold text-[10px] tracking-widest">{metric.label}</p>
            <p className="font-serif text-3xl sm:text-4xl font-bold text-ivory">
              {metric.value === null ? "—" : format(counts[i], metric.decimals)}
            </p>
            <p className="text-xs text-ivory-faint">{metric.sublabel}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
