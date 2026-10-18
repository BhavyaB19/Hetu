"use client";

import { useEffect, useRef } from "react";
import { animate, spring, createScope } from "animejs";

interface LiveScalesProps {
  agree: number;
  partial: number;
  disagree: number;
  totalVotes: number;
  className?: string;
}

export function LiveScales({
  agree,
  partial,
  disagree,
  totalVotes,
  className = "",
}: LiveScalesProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const scopeRef = useRef<ReturnType<typeof createScope> | null>(null);

  // Compute balance angle
  // Left pan = Agree; Right pan = Disagree
  // Downward tilt to the left is negative angle (-deg); downward tilt to the right is positive (+deg).
  let targetAngle = 0;
  let statusText = "No votes yet";

  if (totalVotes > 0) {
    const effAgree = agree + 0.5 * partial;
    const effDisagree = disagree + 0.5 * partial;
    const diff = effDisagree - effAgree; // > 0 means disagree heavier (tilts right/clockwise)
    const netShare = diff / totalVotes; // range [-1, 1]

    // Base max tilt angle = 14 degrees
    const maxTilt = 14;

    // Small sample protection: under 10 votes, cap proportionally
    const sampleFactor = totalVotes < 10 ? totalVotes / 10 : 1;
    targetAngle = netShare * maxTilt * sampleFactor;

    if (Math.abs(targetAngle) < 0.5) {
      statusText = "Evenly Balanced";
    } else if (targetAngle < 0) {
      statusText = "Leaning Agree";
    } else {
      statusText = "Leaning Disagree";
    }
  }

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

      const beam = "#livescales-beam";
      const leftPan = "#livescales-pan-left";
      const rightPan = "#livescales-pan-right";

      if (reduceMotion) {
        animate(beam, { rotate: targetAngle, duration: 0 });
        animate(leftPan, { rotate: -targetAngle, duration: 0 });
        animate(rightPan, { rotate: -targetAngle, duration: 0 });
        return;
      }

      // Spring physics on tilt update
      animate(beam, {
        rotate: targetAngle,
        ease: spring({ bounce: 0.35, duration: 800 }),
      });

      // Hanging pans counter-rotate so they stay vertical
      animate(leftPan, {
        rotate: -targetAngle,
        ease: spring({ bounce: 0.35, duration: 800 }),
      });

      animate(rightPan, {
        rotate: -targetAngle,
        ease: spring({ bounce: 0.35, duration: 800 }),
      });
    });

    return () => {
      scopeRef.current?.revert();
    };
  }, [targetAngle]);

  return (
    <div
      ref={rootRef}
      className={`card p-6 flex flex-col items-center justify-center bg-surface border-gold-line select-none ${className}`}
      aria-label={`Live public opinion scales. Status: ${statusText}`}
    >
      <div className="flex items-center justify-between w-full border-b border-gold-line/40 pb-3 mb-2">
        <span className="eyebrow text-gold text-[10px]">Live Scales of Opinion</span>
        <span className="text-xs font-mono text-ivory-muted px-2 py-0.5 rounded border border-gold-line/60 bg-gold-soft">
          {statusText}
        </span>
      </div>

      <div className="w-full max-w-[340px] h-auto flex items-center justify-center py-2">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 500 450"
          className="w-full h-auto drop-shadow-xl"
          fill="none"
          stroke="currentColor"
          role="img"
          aria-hidden="true"
        >
          <defs>
            <linearGradient id="ls-gold-grad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="var(--color-ivory)" />
              <stop offset="50%" stopColor="var(--color-gold)" />
              <stop offset="100%" stopColor="var(--color-bronze)" />
            </linearGradient>
            <radialGradient id="ls-pan-shadow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="var(--color-surface)" />
              <stop offset="100%" stopColor="var(--color-ink)" />
            </radialGradient>
          </defs>

          {/* Central Fulcrum Stand */}
          <g id="livescales-base" stroke="var(--color-gold)">
            <rect x="175" y="400" width="150" height="24" rx="4" fill="url(#ls-pan-shadow)" strokeWidth="2" />
            <path d="M195 400 L215 340 L285 340 L305 400 Z" fill="url(#ls-pan-shadow)" strokeWidth="1.5" />
            <line x1="250" y1="340" x2="250" y2="110" stroke="url(#ls-gold-grad)" strokeWidth="6" strokeLinecap="round" />
            <circle cx="250" cy="110" r="14" fill="var(--color-surface)" stroke="var(--color-gold)" strokeWidth="3" />
            <circle cx="250" cy="110" r="4" fill="var(--color-gold)" />
            <path d="M250 96 L250 70 M245 75 L255 75" stroke="var(--color-gold)" strokeWidth="2" strokeLinecap="round" />
            <polygon points="250,60 244,72 256,72" fill="var(--color-gold)" />
          </g>

          {/* Dynamic Beam pivoting around (250, 110) */}
          <g id="livescales-beam" style={{ transformOrigin: "250px 110px" }}>
            <path d="M70 110 Q250 100 430 110 Q250 120 70 110 Z" fill="url(#ls-gold-grad)" stroke="var(--color-gold)" strokeWidth="1" />
            <circle cx="250" cy="110" r="6" fill="var(--color-gold)" stroke="var(--color-ink)" strokeWidth="2" />
            <circle cx="85" cy="110" r="4" fill="var(--color-surface)" stroke="var(--color-gold)" strokeWidth="2" />
            <circle cx="415" cy="110" r="4" fill="var(--color-surface)" stroke="var(--color-gold)" strokeWidth="2" />

            {/* Left Pan (Agree) - suspension point (85, 110) */}
            <g id="livescales-pan-left" style={{ transformOrigin: "85px 110px" }}>
              <line x1="85" y1="114" x2="35" y2="250" stroke="var(--color-gold)" strokeWidth="1.5" strokeDasharray="3 3" />
              <line x1="85" y1="114" x2="85" y2="250" stroke="var(--color-gold)" strokeWidth="1" strokeDasharray="3 3" opacity="0.6" />
              <line x1="85" y1="114" x2="135" y2="250" stroke="var(--color-gold)" strokeWidth="1.5" strokeDasharray="3 3" />
              <path d="M25 250 Q85 285 145 250 Q85 255 25 250 Z" fill="url(#ls-pan-shadow)" stroke="var(--color-gold)" strokeWidth="2" />
              <text x="85" y="272" textAnchor="middle" fill="var(--color-ivory)" fontSize="11" fontWeight="bold" fontFamily="var(--font-sans)">
                AGREE
              </text>
              <text x="85" y="290" textAnchor="middle" fill="var(--color-gold)" fontSize="12" fontWeight="600" fontFamily="var(--font-serif)">
                {agree}
              </text>
            </g>

            {/* Right Pan (Disagree) - suspension point (415, 110) */}
            <g id="livescales-pan-right" style={{ transformOrigin: "415px 110px" }}>
              <line x1="415" y1="114" x2="365" y2="250" stroke="var(--color-gold)" strokeWidth="1.5" strokeDasharray="3 3" />
              <line x1="415" y1="114" x2="415" y2="250" stroke="var(--color-gold)" strokeWidth="1" strokeDasharray="3 3" opacity="0.6" />
              <line x1="415" y1="114" x2="465" y2="250" stroke="var(--color-gold)" strokeWidth="1.5" strokeDasharray="3 3" />
              <path d="M355 250 Q415 285 475 250 Q415 255 355 250 Z" fill="url(#ls-pan-shadow)" stroke="var(--color-gold)" strokeWidth="2" />
              <text x="415" y="272" textAnchor="middle" fill="var(--color-ivory)" fontSize="11" fontWeight="bold" fontFamily="var(--font-sans)">
                DISAGREE
              </text>
              <text x="415" y="290" textAnchor="middle" fill="var(--color-gold)" fontSize="12" fontWeight="600" fontFamily="var(--font-serif)">
                {disagree}
              </text>
            </g>
          </g>
        </svg>
      </div>

      {/* Touch / Coarse pointer notice */}
      <div className="w-full flex items-center justify-between text-[11px] text-ivory-faint pt-2 border-t border-gold-line/40">
        <span>Partly agree counts half to each side</span>
        {totalVotes < 10 && totalVotes > 0 && (
          <span className="text-gold">Tilt dampened (&lt;10 votes)</span>
        )}
      </div>
    </div>
  );
}
