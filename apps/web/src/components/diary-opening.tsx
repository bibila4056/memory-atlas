"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { OPENED_KEY } from "@/lib/capture";

const subscribe = () => () => {};
const serverSnapshot = () => "checking";
const browserSnapshot = () => sessionStorage.getItem(OPENED_KEY) ? "open" : "closed";

export function DiaryOpening({ children }: { children: React.ReactNode }) {
  const stage = useRef<HTMLDivElement>(null);
  const content = useRef<HTMLDivElement>(null);
  const initial = useSyncExternalStore(subscribe, browserSnapshot, serverSnapshot);
  const [action, setPhase] = useState<"opening" | "open" | null>(null);
  const phase = action ?? initial;
  useEffect(() => {
    if (phase !== "opening") return;
    const timer = setTimeout(() => {
      sessionStorage.setItem(OPENED_KEY, "true");
      setPhase("open");
    }, 1450);
    return () => clearTimeout(timer);
  }, [phase]);
  function open() {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      sessionStorage.setItem(OPENED_KEY, "true");
      setPhase("open");
    } else {
      const book = stage.current;
      const paper = content.current?.querySelector(".capture-notebook");
      if (book && paper) {
        const from = book.getBoundingClientRect(), to = paper.getBoundingClientRect();
        book.style.position = "fixed";
        book.animate([
          { left: `${from.left}px`, top: `${from.top}px`, width: `${from.width}px`, height: `${from.height}px` },
          { left: `${to.left}px`, top: `${to.top}px`, width: `${to.width}px`, height: `${to.height}px` },
        ], { duration: 1000, easing: "cubic-bezier(.22,.65,.3,1)", fill: "forwards" });
      }
      setPhase("opening");
    }
  }
  return <div className="diary-experience" data-opening-phase={phase}>
    <div ref={content} className="diary-content" inert={phase !== "open"} aria-hidden={phase !== "open"}>{children}</div>
    {phase !== "open" && <div className="diary-entrance" data-phase={phase}>
      <p className="entrance-eyebrow">A place for what stays with you</p>
      <div ref={stage} className="diary-stage">
        <div className="diary-object">
          <div className="diary-page-block" aria-hidden="true" />
          <div className="turning-leaf leaf-two" aria-hidden="true" />
          <div className="turning-leaf leaf-one" aria-hidden="true" />
          <button type="button" className="diary-cover" onClick={open} disabled={phase === "opening"} aria-label="Open your diary">
            <span className="cover-border" aria-hidden="true" />
            <span className="cover-edition">A personal notebook</span>
            <span className="cover-title foil">Memory<br /><em>Atlas</em></span>
            <span className="cover-mark" aria-hidden="true" />
            <span className="cover-caption">Photos. Words. A life remembered.</span>
          </button>
        </div>
      </div>
      <p className="entrance-hint" aria-live="polite">{phase === "opening" ? "Opening your notebook…" : "Open your notebook to begin"}</p>
    </div>}
  </div>;
}
