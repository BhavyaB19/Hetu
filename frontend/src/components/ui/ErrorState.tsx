import React from "react";
import Link from "next/link";

interface ErrorStateProps {
  eyebrow?: string;
  title?: string;
  message?: string;
  retryAction?: () => void;
  className?: string;
}

export function ErrorState({
  eyebrow = "Connection Error",
  title = "Unable to fetch data",
  message = "Could not connect to the Hetu verification server. Please ensure the backend is running and refresh.",
  retryAction,
  className = "",
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={`card flex flex-col items-center justify-center p-8 sm:p-12 text-center border-danger/30 bg-surface ${className}`}
    >
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-danger/40 bg-danger/10 text-danger">
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
            d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
          />
        </svg>
      </div>
      <p className="eyebrow text-danger mb-2">{eyebrow}</p>
      <h3 className="font-serif text-xl sm:text-2xl text-ivory mb-2">{title}</h3>
      <p className="max-w-md text-sm text-ivory-muted leading-relaxed mb-6">{message}</p>
      <div className="flex flex-wrap items-center gap-3">
        {retryAction && (
          <button
            type="button"
            onClick={retryAction}
            className="rounded-md bg-gold px-4 py-2 text-sm font-semibold text-ink hover:bg-bronze transition-colors cursor-pointer"
          >
            Try Again
          </button>
        )}
        <Link
          href="/"
          className="rounded-md border border-gold-line bg-gold-soft px-4 py-2 text-sm font-medium text-gold hover:border-gold hover:text-ivory transition-colors"
        >
          Return Home
        </Link>
      </div>
    </div>
  );
}
