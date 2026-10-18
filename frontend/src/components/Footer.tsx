import React from "react";
import Link from "next/link";

export function Footer() {
  return (
    <footer role="contentinfo" className="mt-auto border-t border-gold-line bg-surface pt-12 pb-8 text-ivory-muted text-sm">
      <div className="mx-auto w-full max-w-6xl px-4 sm:px-6">
        <div className="grid gap-8 md:grid-cols-4 pb-10 border-b border-gold-line/40">
          {/* Brand Col */}
          <div className="md:col-span-2 flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <span className="font-serif text-2xl font-bold text-ivory">Hetu</span>
              <span className="text-xs uppercase tracking-widest text-gold px-2 py-0.5 rounded border border-gold-line bg-gold-soft">
                v2
              </span>
            </div>
            <p className="font-serif italic text-ivory text-base">
              Why it happened. What was said. What India felt.
            </p>
            <p className="text-xs text-ivory-muted leading-relaxed max-w-md">
              Hetu puts three stories about an Indian criminal case side by side: the court&apos;s evidentiary findings,
              the media&apos;s coverage, and the public&apos;s reaction—scoring narrative drift through the Perception Gap Index.
            </p>
          </div>

          {/* Navigation Col */}
          <div className="flex flex-col gap-3">
            <p className="eyebrow text-gold text-xs">Surfaces</p>
            <ul className="flex flex-col gap-2 text-sm">
              <li>
                <Link href="/" className="hover:text-gold transition-colors">
                  Home
                </Link>
              </li>
              <li>
                <Link href="/verdicts" className="hover:text-gold transition-colors">
                  Verdicts
                </Link>
              </li>
              <li>
                <Link href="/jan-mat" className="hover:text-gold transition-colors">
                  Jan Mat
                </Link>
              </li>
              <li>
                <Link href="/live-docket" className="hover:text-gold transition-colors">
                  Live Docket
                </Link>
              </li>
              <li>
                <Link href="/methodology" className="hover:text-gold transition-colors">
                  Methodology &amp; Ethics
                </Link>
              </li>
            </ul>
          </div>

          {/* Ethics & Protocol Col */}
          <div className="flex flex-col gap-3">
            <p className="eyebrow text-gold text-xs">Editorial Standards</p>
            <ul className="flex flex-col gap-2 text-xs text-ivory-muted leading-relaxed">
              <li>
                <strong className="text-ivory font-medium">Pending Trials Policy:</strong> We do not open polls or discussion on pending trials.
              </li>
              <li>
                <strong className="text-ivory font-medium">Privacy Guard:</strong> Strict anonymization of private individuals.
              </li>
              <li>
                <strong className="text-ivory font-medium">Verbatim Proof:</strong> Verifiable quote anchors for judicial findings.
              </li>
              <li>
                <Link href="/admin" className="text-ivory-faint hover:text-gold transition-colors">
                  Admin Portal →
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-ivory-faint">
          <p>© {new Date().getFullYear()} Hetu Public Research. Non-commercial public interest platform.</p>
          <p className="text-center sm:text-right">
            Opinions collected are non-representative. Criticize judicial reasoning, never individuals.
          </p>
        </div>
      </div>
    </footer>
  );
}
