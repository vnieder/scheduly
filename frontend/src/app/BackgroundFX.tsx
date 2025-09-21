"use client";

import { useEffect, useRef } from "react";


export default function BackgroundFX() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const blobsRef = useRef<HTMLDivElement[]>([]);
  const velocitiesRef = useRef<{ vx: number; vy: number }[]>([]);

  // Setup and interaction
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const blobNodes = blobsRef.current;
    if (!blobNodes.length) return;

    const velocities = blobNodes.map(() => ({ vx: 0, vy: 0 }));
    velocitiesRef.current = velocities;

    let mouseX = 0;
    let mouseY = 0;
    let hasMouse = false;

    const onPointerMove = (e: PointerEvent) => {
      const rect = container.getBoundingClientRect();
      mouseX = e.clientX - rect.left;
      mouseY = e.clientY - rect.top;
      hasMouse = true;
    };

    const onPointerLeave = () => {
      hasMouse = false;
    };

    container.addEventListener("pointermove", onPointerMove, { passive: true });
    container.addEventListener("pointerleave", onPointerLeave, {
      passive: true,
    });

    let rafId = 0;

    const tick = () => {

      for (let i = 0; i < blobNodes.length; i++) {
        const node = blobNodes[i];
        const vel = velocities[i];

        // Get current transform translate of node
        const current = node.dataset.pos
          ? JSON.parse(node.dataset.pos)
          : { x: 0, y: 0 };

        // Attraction back to origin (spring)
        const originX = parseFloat(node.dataset.ox || "0");
        const originY = parseFloat(node.dataset.oy || "0");
        const dx0 = originX - current.x;
        const dy0 = originY - current.y;

        const springStrength = 0.02; // how strongly it returns
        vel.vx += dx0 * springStrength;
        vel.vy += dy0 * springStrength;

        // Mouse repulsion
        if (hasMouse) {
          // Compute position in container space
          const baseX =
            originX +
            (node.dataset.baseLeft ? parseFloat(node.dataset.baseLeft) : 0);
          const baseY =
            originY +
            (node.dataset.baseTop ? parseFloat(node.dataset.baseTop) : 0);

          const x = baseX + current.x;
          const y = baseY + current.y;

          const mdx = x - mouseX;
          const mdy = y - mouseY;
          const distSq = mdx * mdx + mdy * mdy;
          const minDist = 160; // px
          const minDistSq = minDist * minDist;
          if (distSq < minDistSq) {
            const dist = Math.sqrt(distSq) || 0.0001;
            const force = (1 - dist / minDist) * 1.2; // scale
            vel.vx += (mdx / dist) * force;
            vel.vy += (mdy / dist) * force;
          }
        }

        // Damping
        const damping = 0.9;
        vel.vx *= damping;
        vel.vy *= damping;

        // Integrate
        current.x += vel.vx;
        current.y += vel.vy;

        // Store and apply transform. We only translate; scale/rotate remain CSS animations.
        node.dataset.pos = JSON.stringify(current);
        node.style.transform = `translate(${current.x}px, ${current.y}px)`;
      }

      rafId = requestAnimationFrame(tick);
    };

    rafId = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(rafId);
      container.removeEventListener("pointermove", onPointerMove);
      container.removeEventListener("pointerleave", onPointerLeave);
    };
  }, []);

  // Register each blob ref and seed origin positions
  const registerBlob = (index: number) => (el: HTMLDivElement | null) => {
    if (!el) return;
    blobsRef.current[index] = el;
    // origin offsets relative to own element (start at 0,0)
    el.dataset.pos = JSON.stringify({ x: 0, y: 0 });
    el.dataset.ox = "0";
    el.dataset.oy = "0";

    // Save initial absolute offsets from container (for distance calc)
    const left = el.style.left ? parseFloat(el.style.left) : 0;
    const top = el.style.top ? parseFloat(el.style.top) : 0;

    // Convert right/bottom positioning into left/top by measuring container size later at runtime.
    // Here we store baseLeft/baseTop as provided to estimate position for interactions.
    if (!Number.isNaN(left))
      el.dataset.baseLeft = `${
        (left / 100) *
        (blobsRef.current[index]?.parentElement?.clientWidth || 0)
      }`;
    if (!Number.isNaN(top))
      el.dataset.baseTop = `${
        (top / 100) *
        (blobsRef.current[index]?.parentElement?.clientHeight || 0)
      }`;
  };

  // The blob positions match the previous layout inline styles
  return (
    <div
      ref={containerRef}
      className="fixed inset-0 -z-10 overflow-hidden glow-blob-wrap"
    >
      <div className="ambient-gradient ambient-gradient--a" />
      <div className="ambient-gradient ambient-gradient--b" />
      <div className="ambient-gradient ambient-gradient--c" />
      <div className="bg-grid-soft" />

      <div
        ref={registerBlob(0)}
        className="glow-blob glow-blob--cyan"
        style={{ top: "-12%", left: "-8%" }}
      />
      <div
        ref={registerBlob(1)}
        className="glow-blob glow-blob--violet"
        style={{ bottom: "-12%", right: "-12%" }}
      />
      <div
        ref={registerBlob(2)}
        className="glow-blob glow-blob--orange"
        style={{ top: "18%", right: "18%" }}
      />
      <div
        ref={registerBlob(3)}
        className="glow-blob glow-blob--pink"
        style={{ bottom: "12%", left: "12%" }}
      />
    </div>
  );
}
