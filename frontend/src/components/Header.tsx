"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Home" },
  { href: "/verdicts", label: "Verdicts" },
  { href: "/jan-mat", label: "Jan Mat" },
  { href: "/live-docket", label: "Live Docket" },
  { href: "/methodology", label: "Methodology" },
];

export function Header() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <header role="banner" className="border-b border-gold-line bg-ink/90 backdrop-blur-md sticky top-0 z-40">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center gap-2.5 group">
            <span className="font-serif text-2xl font-bold tracking-wide text-ivory group-hover:text-gold transition-colors">
              Hetu
            </span>
            <span className="hidden sm:inline-block border-l border-gold-line pl-3 text-xs tracking-wider uppercase text-ivory-faint font-sans">
              Perception Gap
            </span>
          </Link>
        </div>

        {/* Desktop Nav */}
        <nav role="navigation" aria-label="Main Navigation" className="hidden md:flex items-center gap-1 sm:gap-2">
          {NAV_ITEMS.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                  active
                    ? "bg-gold-soft text-gold border border-gold-line font-semibold"
                    : "text-ivory-muted hover:text-ivory hover:bg-surface"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Mobile menu button */}
        <div className="flex md:hidden items-center">
          <button
            type="button"
            onClick={() => setMobileMenuOpen((prev) => !prev)}
            aria-expanded={mobileMenuOpen}
            aria-label="Toggle navigation menu"
            className="rounded-md p-2 text-ivory-muted hover:bg-surface hover:text-ivory focus:outline-none focus:ring-1 focus:ring-gold"
          >
            <svg
              className="h-6 w-6 stroke-current"
              fill="none"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              {mobileMenuOpen ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile Drawer / Dropdown */}
      {mobileMenuOpen && (
        <div className="border-t border-gold-line bg-surface md:hidden px-4 py-4 space-y-2">
          <nav aria-label="Mobile Navigation" className="flex flex-col gap-1">
            {NAV_ITEMS.map((item) => {
              const active = isActive(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    active
                      ? "bg-gold-soft text-gold border border-gold-line font-semibold"
                      : "text-ivory-muted hover:text-ivory hover:bg-ink"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      )}
    </header>
  );
}
