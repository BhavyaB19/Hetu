import Link from "next/link";

import { JaaliField } from "@/components/jaali/JaaliPatterns";

const COLUMNS = [
  {
    title: "Read",
    links: [
      { href: "/verdicts", label: "Verdicts" },
      { href: "/live-docket", label: "Live Docket" },
      { href: "/methodology", label: "Methodology" },
    ],
  },
  {
    title: "Take part",
    links: [
      { href: "/jan-mat", label: "Jan Mat" },
      { href: "/methodology#corrections", label: "Request a correction" },
    ],
  },
  {
    title: "How it works",
    links: [
      { href: "/methodology", label: "Perception Gap Index" },
      { href: "/methodology#sources", label: "Sources and robots.txt" },
      { href: "/methodology#privacy", label: "Anonymisation" },
    ],
  },
];

/** The plinth: an ink block under a band of carved screen. */
export function Footer() {
  return (
    <footer role="contentinfo" className="reverse mt-auto">
      <JaaliField variant="ink" className="block h-11 w-full border-b border-gold-line" />
      <div className="mx-auto grid w-full max-w-[90rem] gap-10 px-4 py-14 sm:px-8 md:grid-cols-[1.4fr_1fr_1fr_1fr] lg:px-12">
        <div className="flex flex-col gap-3">
          <p className="font-serif text-2xl leading-snug text-ivory">Why it happened. What was said. What India felt.</p>
          <p className="max-w-sm text-sm leading-relaxed text-ivory-muted">
            Hetu is an independent research project. It is not legal advice and it does not predict outcomes.
          </p>
        </div>
        {COLUMNS.map((col) => (
          <div key={col.title}>
            <p className="eyebrow mb-4">{col.title}</p>
            <ul className="flex flex-col gap-2 text-sm text-ivory-muted">
              {col.links.map((l) => (
                <li key={l.label}>
                  <Link href={l.href} className="hover:text-ivory">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-gold-line">
        <div className="mx-auto flex w-full max-w-[90rem] flex-col justify-between gap-2 px-4 py-5 text-xs text-ivory-faint sm:flex-row sm:px-8 lg:px-12">
          <span>© {new Date().getFullYear()} Hetu</span>
          <span>Sub judice: no polls or discussion on pending trials.</span>
          <Link href="/admin" className="hover:text-ivory">
            Curators
          </Link>
        </div>
      </div>
    </footer>
  );
}
