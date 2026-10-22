"use client";

import { animate, createScope, onScroll, spring } from "animejs";
import { useEffect, useRef } from "react";

import { MAX_TILT_DEG } from "@/lib/balance";

/**
 * Vector scales that settle to `lean` when scrolled into view: left pan Media, right pan
 * Court. Used when the rendered scales clip is not available.
 */
export function BalanceScales({ lean }: { lean: number }) {
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    // Left pan down is a counter-clockwise (negative) beam rotation; the pans hang straight.
    const beam = -lean * MAX_TILT_DEG;
    const scope = createScope({ root, mediaQueries: { reduceMotion: "(prefers-reduced-motion: reduce)" } }).add(
      (self) => {
        if (self?.matches.reduceMotion) {
          animate("#bs-beam", { rotate: beam, duration: 0 });
          animate(".bs-pan", { rotate: -beam, duration: 0 });
          return;
        }
        const ease = spring({ bounce: 0.35, duration: 1200 });
        animate("#bs-beam", { rotate: [0, beam], ease, autoplay: onScroll({ target: root, enter: "bottom center" }) });
        animate(".bs-pan", { rotate: [0, -beam], ease, autoplay: onScroll({ target: root, enter: "bottom center" }) });
      },
    );
    return () => scope.revert();
  }, [lean]);

  return (
    <div ref={rootRef} className="mx-auto w-full max-w-md">
      <svg viewBox="0 0 500 330" className="h-auto w-full" fill="none" aria-hidden="true">
        <g stroke="var(--color-gold)">
          <path d="M195 310 L215 250 L285 250 L305 310 Z" fill="var(--color-surface)" strokeWidth="1.5" />
          <line x1="250" y1="250" x2="250" y2="70" strokeWidth="5" strokeLinecap="round" />
        </g>
        <g id="bs-beam" style={{ transformOrigin: "250px 70px" }}>
          <line x1="70" y1="70" x2="430" y2="70" stroke="var(--color-gold)" strokeWidth="5" strokeLinecap="round" />
          <circle cx="250" cy="70" r="9" fill="var(--color-surface)" stroke="var(--color-gold)" strokeWidth="3" />
          {[
            { x: 85, label: "MEDIA" },
            { x: 415, label: "COURT" },
          ].map(({ x, label }) => (
            <g key={label} className="bs-pan" style={{ transformOrigin: `${x}px 70px` }}>
              <line x1={x} y1={72} x2={x - 50} y2={190} stroke="var(--color-gold)" strokeWidth="1.5" />
              <line x1={x} y1={72} x2={x + 50} y2={190} stroke="var(--color-gold)" strokeWidth="1.5" />
              <path
                d={`M${x - 60} 190 Q${x} 225 ${x + 60} 190 Z`}
                fill="var(--color-surface)"
                stroke="var(--color-gold)"
                strokeWidth="2"
              />
              <text
                x={x}
                y={212}
                textAnchor="middle"
                fill="var(--color-ivory-muted)"
                fontSize="12"
                letterSpacing="1.5"
                fontFamily="var(--font-sans)"
              >
                {label}
              </text>
            </g>
          ))}
        </g>
      </svg>
    </div>
  );
}
