import React from "react";
import Link from "next/link";

interface EmptyStateProps {
  eyebrow?: string;
  title: string;
  description: string;
  actionHref?: string;
  actionLabel?: string;
  icon?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  eyebrow = "No Records Available",
  title,
  description,
  actionHref,
  actionLabel,
  icon,
  className = "",
}: EmptyStateProps) {
  return (
    <div
      role="status"
      className={`card flex flex-col items-center justify-center p-8 sm:p-12 text-center ${className}`}
    >
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-gold-line bg-gold-soft text-gold">
        {icon || (
          <svg
            className="h-6 w-6 stroke-current"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
            />
          </svg>
        )}
      </div>
      {eyebrow && <p className="eyebrow mb-2">{eyebrow}</p>}
      <h3 className="font-serif text-xl sm:text-2xl text-ivory mb-2">{title}</h3>
      <p className="max-w-md text-sm text-ivory-muted leading-relaxed mb-6">{description}</p>
      {actionHref && actionLabel && (
        <Link
          href={actionHref}
          className="inline-flex items-center gap-2 rounded-md border border-gold-line bg-gold-soft px-4 py-2 text-sm font-medium text-gold hover:border-gold hover:text-ivory transition-colors"
        >
          {actionLabel}
        </Link>
      )}
    </div>
  );
}
