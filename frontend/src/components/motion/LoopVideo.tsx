"use client";

import { useEffect, useRef, type ReactNode } from "react";

type Props = {
  /** Null when the video has not been added; the fallback is shown instead. */
  video?: { mp4: string; webm?: string };
  label: string;
  className?: string;
  fallback?: ReactNode;
};

/** A short muted loop. Paused under reduced motion and on a hidden tab. */
export function LoopVideo({ video, label, className = "", fallback = null }: Props) {
  const ref = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => {
      if (reduce.matches || document.hidden) el.pause();
      else void el.play().catch(() => {});
    };
    sync();
    document.addEventListener("visibilitychange", sync);
    reduce.addEventListener("change", sync);
    return () => {
      document.removeEventListener("visibilitychange", sync);
      reduce.removeEventListener("change", sync);
    };
  }, [video]);

  if (!video) return <>{fallback}</>;

  return (
    <video ref={ref} muted loop playsInline preload="auto" aria-label={label} className={className}>
      {video.webm && <source src={video.webm} type="video/webm" />}
      <source src={video.mp4} type="video/mp4" />
    </video>
  );
}
