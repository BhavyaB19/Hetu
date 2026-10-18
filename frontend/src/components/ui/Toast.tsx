"use client";

import React, { createContext, useContext, useState, useCallback } from "react";

export type ToastType = "info" | "success" | "warning" | "error";

interface Toast {
  id: string;
  type: ToastType;
  title?: string;
  message: string;
}

interface ToastContextValue {
  showToast: (message: string, options?: { type?: ToastType; title?: string }) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback(
    (message: string, options?: { type?: ToastType; title?: string }) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      const newToast: Toast = {
        id,
        message,
        type: options?.type || "info",
        title: options?.title,
      };

      setToasts((prev) => [...prev, newToast]);

      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 4500);
    },
    []
  );

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div
        role="region"
        aria-label="Notifications"
        aria-live="polite"
        className="fixed bottom-5 right-5 z-50 flex flex-col gap-2.5 max-w-sm pointer-events-none"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role="status"
            className={`pointer-events-auto flex items-start gap-3 p-4 rounded-lg border shadow-xl backdrop-blur-md transition-all ${
              toast.type === "success"
                ? "bg-surface/95 border-ok/50 text-ivory"
                : toast.type === "error"
                ? "bg-surface/95 border-danger/60 text-ivory"
                : toast.type === "warning"
                ? "bg-surface/95 border-gold/70 text-ivory"
                : "bg-surface/95 border-gold-line text-ivory"
            }`}
          >
            <div className="shrink-0 mt-0.5">
              {toast.type === "success" && (
                <svg className="h-4 w-4 text-ok" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
              {toast.type === "error" && (
                <svg className="h-4 w-4 text-danger" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              )}
              {toast.type === "warning" && (
                <svg className="h-4 w-4 text-gold" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              )}
              {toast.type === "info" && (
                <svg className="h-4 w-4 text-gold" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              )}
            </div>

            <div className="flex-1 text-xs">
              {toast.title && <p className="font-semibold text-ivory mb-0.5">{toast.title}</p>}
              <p className="text-ivory-muted leading-relaxed">{toast.message}</p>
            </div>

            <button
              type="button"
              onClick={() => removeToast(toast.id)}
              aria-label="Dismiss notification"
              className="shrink-0 text-ivory-faint hover:text-ivory p-0.5 rounded cursor-pointer"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
