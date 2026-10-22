"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Fragment, useState } from "react";

const NAV_ITEMS = [
  { href: "/", label: "Home" },
  { href: "/verdicts", label: "Verdicts" },
  { href: "/jan-mat", label: "Jan Mat" },
  { href: "/live-docket", label: "Live Docket" },
  { href: "/methodology", label: "Method" },
];

/** The lintel: wordmark, the five surfaces separated by lozenges, and the one primary action. */
export function Header() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));

  return (
    <header role="banner" className="sticky top-0 z-40 border-b border-gold-line bg-surface">
      <div className="mx-auto grid h-20 w-full max-w-[90rem] grid-cols-[1fr_auto] items-center gap-6 px-4 sm:px-8 lg:grid-cols-[1fr_auto_1fr] lg:px-12">
        <Link href="/" className="flex items-baseline gap-3" aria-label="Hetu, home">
          <span className="font-serif text-3xl tracking-wide text-ivory">Hetu</span>
          <span lang="hi" className="font-deva text-base text-gold">
            हेतु
          </span>
        </Link>

        <nav aria-label="Main" className="hidden lg:block">
          <ul className="flex items-center gap-5 text-sm">
            {NAV_ITEMS.map((item, i) => {
              const active = isActive(item.href);
              return (
                <Fragment key={item.href}>
                  {i > 0 && <li aria-hidden className="lozenge opacity-60" />}
                  <li>
                    <Link
                      href={item.href}
                      aria-current={active ? "page" : undefined}
                      className={`block border-b-2 py-1 transition-colors ${
                        active ? "border-gold text-ivory" : "border-transparent text-ivory-muted hover:text-ivory"
                      }`}
                    >
                      {item.label}
                    </Link>
                  </li>
                </Fragment>
              );
            })}
          </ul>
        </nav>

        <div className="flex items-center justify-end gap-3">
          <Link href="/verdicts" className="btn-seal hidden sm:inline-flex">
            Read a verdict
          </Link>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-controls="mobile-nav"
            aria-label={open ? "Close menu" : "Open menu"}
            className="p-2 text-ivory-muted hover:text-ivory focus-visible:outline-2 focus-visible:outline-gold lg:hidden"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden>
              {open ? <path d="M6 18L18 6M6 6l12 12" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
            </svg>
          </button>
        </div>
      </div>

      {open && (
        <nav id="mobile-nav" aria-label="Main" className="border-t border-gold-line bg-surface px-4 py-3 lg:hidden">
          <ul className="flex flex-col">
            {NAV_ITEMS.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  onClick={() => setOpen(false)}
                  aria-current={isActive(item.href) ? "page" : undefined}
                  className={`flex items-center gap-3 border-b border-gold-line py-3 text-sm ${
                    isActive(item.href) ? "text-gold" : "text-ivory-muted"
                  }`}
                >
                  <span aria-hidden className="lozenge" />
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
          <Link href="/verdicts" onClick={() => setOpen(false)} className="btn-seal mt-4 sm:hidden">
            Read a verdict
          </Link>
        </nav>
      )}
    </header>
  );
}
