"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { animate, createScope } from "animejs";

export function ScalesHero() {
  const rootRef = useRef<HTMLDivElement>(null);
  const scopeRef = useRef<ReturnType<typeof createScope> | null>(null);

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
        animate("#beam", { rotate: 0, duration: 0 });
        animate("#pan-left", { rotate: 0, duration: 0 });
        animate("#pan-right", { rotate: 0, duration: 0 });
        return;
      }

      // Gentle, dignified idle sway of crossbeam (pivot at center 250, 110)
      const animBeam = animate("#beam", {
        rotate: [-3.8, 3.8],
        duration: 3600,
        ease: "inOutSine",
        loop: true,
        alternate: true,
      });

      // Compensatory counter-rotation for hanging pans to simulate gravity
      const animPanLeft = animate("#pan-left", {
        rotate: [3.8, -3.8],
        duration: 3600,
        ease: "inOutSine",
        loop: true,
        alternate: true,
      });

      const animPanRight = animate("#pan-right", {
        rotate: [3.8, -3.8],
        duration: 3600,
        ease: "inOutSine",
        loop: true,
        alternate: true,
      });

      // Handle pause on tab hidden
      const onVisibility = () => {
        if (document.hidden) {
          animBeam.pause();
          animPanLeft.pause();
          animPanRight.pause();
        } else if (!reduceMotion) {
          animBeam.play();
          animPanLeft.play();
          animPanRight.play();
        }
      };
      document.addEventListener("visibilitychange", onVisibility);

      return () => document.removeEventListener("visibilitychange", onVisibility);
    });

    return () => {
      scopeRef.current?.revert();
    };
  }, []);

  return (
    <div ref={rootRef} className="flex flex-col lg:flex-row items-center justify-between gap-10 py-6 sm:py-12">
      {/* Hero Text */}
      <div className="flex flex-col items-start gap-6 max-w-xl text-left">
        <div className="inline-flex items-center gap-2 rounded-full border border-gold-line bg-gold-soft px-3.5 py-1 text-xs text-gold">
          <span className="h-1.5 w-1.5 rounded-full bg-gold animate-pulse" />
          <span>Indian Criminal Jurisprudence &amp; Media Research</span>
        </div>

        <h1 className="font-serif text-4xl sm:text-6xl text-ivory leading-[1.12] tracking-tight">
          One verdict. <br />
          <span className="text-gold italic font-normal">Three stories.</span> <br />
          One connected view.
        </h1>

        <p className="text-base sm:text-lg text-ivory-muted leading-relaxed max-w-lg">
          Hetu puts the court&apos;s evidentiary findings side-by-side with news headlines and public sentiment,
          measuring narrative drift through the <strong className="text-ivory font-medium">Perception Gap Index</strong>.
        </p>

        <div className="flex flex-wrap items-center gap-4 pt-2">
          <Link
            href="/verdicts"
            className="rounded-md bg-gold px-6 py-3 text-sm font-semibold text-ink hover:bg-bronze transition-colors shadow-lg"
          >
            Explore Verdicts →
          </Link>
          <Link
            href="/live-docket"
            className="rounded-md border border-gold-line bg-gold-soft px-6 py-3 text-sm font-medium text-gold hover:border-gold hover:text-ivory transition-colors"
          >
            See Live Docket
          </Link>
          <Link
            href="/jan-mat"
            className="rounded-md px-4 py-3 text-sm font-medium text-ivory-muted hover:text-gold transition-colors"
          >
            Vote in Jan Mat
          </Link>
        </div>
      </div>

      {/* Hero Vector Scales Art */}
      <div className="w-full max-w-[380px] sm:max-w-[420px] flex items-center justify-center p-4">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 500 450"
          className="w-full h-auto drop-shadow-2xl select-none"
          fill="none"
          stroke="currentColor"
          aria-label="Scales of Justice balancing judicial findings and public perceptions"
          role="img"
        >
          <defs>
            <linearGradient id="hero-scales-gold" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="var(--color-ivory)" />
              <stop offset="50%" stopColor="var(--color-gold)" />
              <stop offset="100%" stopColor="var(--color-bronze)" />
            </linearGradient>
            <radialGradient id="hero-pan-shadow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="var(--color-surface)" />
              <stop offset="100%" stopColor="var(--color-ink)" />
            </radialGradient>
          </defs>

          {/* Fulcrum Pillar & Base */}
          <g id="base" stroke="var(--color-gold)">
            <rect x="175" y="400" width="150" height="24" rx="4" fill="url(#hero-pan-shadow)" strokeWidth="2" />
            <path d="M195 400 L215 340 L285 340 L305 400 Z" fill="url(#hero-pan-shadow)" strokeWidth="1.5" />
            <line x1="250" y1="340" x2="250" y2="110" stroke="url(#hero-scales-gold)" strokeWidth="6" strokeLinecap="round" />
            <circle cx="250" cy="110" r="14" fill="var(--color-surface)" stroke="var(--color-gold)" strokeWidth="3" />
            <circle cx="250" cy="110" r="4" fill="var(--color-gold)" />
            <path d="M250 96 L250 70 M245 75 L255 75" stroke="var(--color-gold)" strokeWidth="2" strokeLinecap="round" />
            <polygon points="250,60 244,72 256,72" fill="var(--color-gold)" />
          </g>

          {/* Crossbeam with Pivot at (250, 110) */}
          <g id="beam" style={{ transformOrigin: "250px 110px" }}>
            <path d="M70 110 Q250 100 430 110 Q250 120 70 110 Z" fill="url(#hero-scales-gold)" stroke="var(--color-gold)" strokeWidth="1" />
            <circle cx="250" cy="110" r="6" fill="var(--color-gold)" stroke="var(--color-ink)" strokeWidth="2" />
            <circle cx="85" cy="110" r="4" fill="var(--color-surface)" stroke="var(--color-gold)" strokeWidth="2" />
            <circle cx="415" cy="110" r="4" fill="var(--color-surface)" stroke="var(--color-gold)" strokeWidth="2" />

            {/* Left Pan (Suspension point 85, 110) */}
            <g id="pan-left" style={{ transformOrigin: "85px 110px" }}>
              <line x1="85" y1="114" x2="35" y2="250" stroke="var(--color-gold)" strokeWidth="1.5" strokeDasharray="3 3" />
              <line x1="85" y1="114" x2="85" y2="250" stroke="var(--color-gold)" strokeWidth="1" strokeDasharray="3 3" opacity="0.6" />
              <line x1="85" y1="114" x2="135" y2="250" stroke="var(--color-gold)" strokeWidth="1.5" strokeDasharray="3 3" />
              <path d="M25 250 Q85 285 145 250 Q85 255 25 250 Z" fill="url(#hero-pan-shadow)" stroke="var(--color-gold)" strokeWidth="2" />
              <text x="85" y="272" textAnchor="middle" fill="var(--color-ivory-muted)" fontSize="10" letterSpacing="1" fontFamily="var(--font-sans)">
                COURT
              </text>
            </g>

            {/* Right Pan (Suspension point 415, 110) */}
            <g id="pan-right" style={{ transformOrigin: "415px 110px" }}>
              <line x1="415" y1="114" x2="365" y2="250" stroke="var(--color-gold)" strokeWidth="1.5" strokeDasharray="3 3" />
              <line x1="415" y1="114" x2="415" y2="250" stroke="var(--color-gold)" strokeWidth="1" strokeDasharray="3 3" opacity="0.6" />
              <line x1="415" y1="114" x2="465" y2="250" stroke="var(--color-gold)" strokeWidth="1.5" strokeDasharray="3 3" />
              <path d="M355 250 Q415 285 475 250 Q415 255 355 250 Z" fill="url(#hero-pan-shadow)" stroke="var(--color-gold)" strokeWidth="2" />
              <text x="415" y="272" textAnchor="middle" fill="var(--color-ivory-muted)" fontSize="10" letterSpacing="1" fontFamily="var(--font-sans)">
                PUBLIC
              </text>
            </g>
          </g>
        </svg>
      </div>
    </div>
  );
}
