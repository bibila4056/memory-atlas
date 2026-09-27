"use client";

import { useEffect, useRef, useState } from "react";
import { MemorySpread } from "./memory-spread";
import { assertRevision, type ResolvedVisualPlan } from "@/lib/plan";

export function SpreadViewer({ plan }: { plan: ResolvedVisualPlan }) {
  const [acceptedPlan, setAcceptedPlan] = useState(plan);
  if (plan !== acceptedPlan) {
    assertRevision(acceptedPlan, plan);
    setAcceptedPlan(plan);
  }
  const viewport = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState<{ width: number; height: number } | null>(null);
  const [zoomed, setZoomed] = useState(false);
  useEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => {
      setSize({ width: entry.contentRect.width, height: entry.contentRect.height });
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [plan.canvas.width, plan.canvas.height]);
  const scale = size ? (zoomed
    ? 1
    : Math.min(size.width / plan.canvas.width, size.height / plan.canvas.height, 1)) : 0;
  return (
    <section className="spread-viewer" aria-label="Spread viewer">
      <div className="viewer-heading">
        <div className="viewer-label"><span className="small-rule" /> A memory, on paper</div>
        <div className="zoom-controls" aria-label="View size">
          <button type="button" aria-pressed={!zoomed} onClick={() => setZoomed(false)}>Fit spread</button>
          <span aria-hidden="true" />
          <button type="button" aria-pressed={zoomed} onClick={() => setZoomed(true)}>Actual size</button>
        </div>
      </div>
      <div className="spread-viewport" ref={viewport} data-testid="spread-viewport" tabIndex={0}
        aria-label={zoomed ? "Reading view. Scroll to explore both pages." : "Complete spread, fitted to the window."}>
        <div className="spread-frame" style={{ width: plan.canvas.width * scale, height: plan.canvas.height * scale, visibility: size === null ? "hidden" : "visible" }}>
          <div className="spread-scale" style={{ transform: `scale(${scale})` }}>
            <MemorySpread plan={acceptedPlan} />
          </div>
        </div>
      </div>
      <div className="viewer-bottom">
        <span className="view-hint">{zoomed ? "Scroll across to explore both pages" : "Two pages. One quiet moment."}</span>
        <span className="page-count">01 <span aria-hidden="true">—</span> 02</span>
      </div>
      <p className="sample-disclosure">Composition study · Temporary sample imagery & words</p>
    </section>
  );
}
