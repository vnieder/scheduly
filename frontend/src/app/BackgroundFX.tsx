"use client";

import { useEffect, useRef } from "react";

export default function BackgroundFX() {
  const gradientRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const element = gradientRef.current;
    if (!element) return;

    // Respect reduced motion preferences
    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;
    if (reduceMotion) {
      element.style.setProperty("--x", "50%");
      element.style.setProperty("--y", "40%");
      return;
    }

    let rafId = 0;
    const update = (xPct: number, yPct: number) => {
      element.style.setProperty("--x", `${xPct}%`);
      element.style.setProperty("--y", `${yPct}%`);
    };

    const onMouseMove = (e: MouseEvent) => {
      if (rafId) return;
      rafId = requestAnimationFrame(() => {
        const x = (e.clientX / window.innerWidth) * 100;
        const y = (e.clientY / window.innerHeight) * 100;
        update(x, y);
        rafId = 0;
      });
    };

    const onTouchMove = (e: TouchEvent) => {
      const t = e.touches[0];
      if (!t) return;
      if (rafId) return;
      rafId = requestAnimationFrame(() => {
        const x = (t.clientX / window.innerWidth) * 100;
        const y = (t.clientY / window.innerHeight) * 100;
        update(x, y);
        rafId = 0;
      });
    };

    // Initial center
    update(50, 40);

    window.addEventListener("mousemove", onMouseMove, { passive: true });
    window.addEventListener("touchmove", onTouchMove, { passive: true });

    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("touchmove", onTouchMove);
      if (rafId) cancelAnimationFrame(rafId);
    };
  }, []);

  return <div ref={gradientRef} className="bg-mouse-gradient" />;
}
