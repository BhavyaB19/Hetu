import type { ReactNode } from "react";

/** A numbered section opening: a large folio number, a kicker, the heading and one line of context. */
export function SectionHead({ no, kicker, title, id, children }: { no: string; kicker: ReactNode; title: string; id: string; children?: ReactNode }) {
  return (
    <div className="mb-12 grid gap-4 sm:mb-14 md:grid-cols-[13rem_1fr] md:items-end md:gap-12">
      <span aria-hidden className="font-serif text-7xl leading-[0.8] text-stone-deep md:text-8xl">
        {no}
      </span>
      <div>
        <p className="eyebrow">{kicker}</p>
        <h2 id={id} className="mt-3 font-serif text-3xl leading-tight text-ivory sm:text-[2.75rem]">
          {title}
        </h2>
        {children && <p className="mt-3 max-w-2xl text-base leading-relaxed text-ivory-muted">{children}</p>}
      </div>
    </div>
  );
}
