"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { FARM_CANVAS, FARM_ELEMENTS, FARM_STORY, FARM_TEXT, type FarmProvenance } from "@/lib/farm-day";
import styles from "./farm-day-spread.module.css";

const TREATMENT_LABEL: Record<FarmProvenance["treatment"], string> = {
  PRESERVE: "Preserved",
  DISTILL: "Distilled",
  AUTHOR: "Your words",
};

function useFit(ref: React.RefObject<HTMLDivElement | null>) {
  const [scale, setScale] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => setScale(Math.min(entry.contentRect.width / FARM_CANVAS.width, entry.contentRect.height / FARM_CANVAS.height)));
    observer.observe(el);
    return () => observer.disconnect();
  }, [ref]);
  return scale;
}

function useEdits() {
  const key = "memory-atlas.spread-edits.farm-day";
  const [edits, setEdits] = useState<Record<string, string>>(() => {
    if (typeof window === "undefined") return {};
    try { return JSON.parse(localStorage.getItem(key) ?? "{}"); } catch { return {}; }
  });
  const save = useCallback((id: string, value: string) => setEdits((current) => {
    const next = { ...current, [id]: value };
    try { localStorage.setItem(key, JSON.stringify(next)); } catch { /* edit lasts for this visit */ }
    return next;
  }), []);
  return [edits, save] as const;
}

function Editable({ id, as: Tag = "p", className, value, edits, onSave, onFocus, onBlur }: {
  id: string; as?: "p" | "h1"; className?: string; value: string; edits: Record<string, string>;
  onSave: (id: string, value: string) => void; onFocus?: () => void; onBlur?: () => void;
}) {
  const shown = edits[id] ?? value;
  return <Tag className={`${className ?? ""} editable`} contentEditable suppressContentEditableWarning suppressHydrationWarning spellCheck={false}
    onFocus={onFocus} onBlur={(event) => { const next = event.currentTarget.innerText.trim(); if (next && next !== shown) onSave(id, next); onBlur?.(); }}
    onKeyDown={(event) => { if (event.key === "Escape" || (event.key === "Enter" && Tag === "h1")) { event.preventDefault(); event.currentTarget.blur(); } }}>{shown}</Tag>;
}

export function FarmDaySpread() {
  const stage = useRef<HTMLDivElement>(null);
  const scale = useFit(stage);
  const [focus, setFocus] = useState<string | null>(null);
  const [edits, saveEdit] = useEdits();
  const textProvenance = Object.fromEntries(FARM_TEXT.map((item) => [item.id, {
    label: "Your memory", treatment: "AUTHOR", detail: "Lightly revised from your words · editable on the page", source_ids: ["author-note-farm-day"],
  } satisfies FarmProvenance]));
  const provenance: Record<string, FarmProvenance> = {
    ...Object.fromEntries(FARM_ELEMENTS.map((el) => [el.id, el.provenance])),
    ...textProvenance,
  };
  const active = focus ? provenance[focus] : null;
  const hover = (id: string) => ({ onMouseEnter: () => setFocus(id), onMouseLeave: () => setFocus(null), "data-focus": focus === id || undefined });
  const place = (el: { x: number; y: number; w: number; h: number; r?: number; z?: number }) => ({
    left: el.x, top: el.y, width: el.w, height: el.h, zIndex: el.z ?? 1, "--r": `${el.r ?? 0}deg`,
  } as React.CSSProperties);
  const editProps = { edits, onSave: saveEdit };

  return <div className="collage-wrap">
    <div className="collage-stage" ref={stage}>
      <div className="collage-frame" style={{ width: FARM_CANVAS.width * scale, height: FARM_CANVAS.height * scale, visibility: scale ? "visible" : "hidden" }}>
        <article className={`collage${focus ? " is-inspecting" : ""}`} aria-label={`Memory spread: ${FARM_STORY.weekday}, ${FARM_STORY.date}`}
          style={{ width: FARM_CANVAS.width, height: FARM_CANVAS.height, transform: `scale(${scale})` }}>
          <div className="collage-page collage-page--left" aria-hidden="true" />
          <div className="collage-page collage-page--right" aria-hidden="true" />
          <div className="collage-gutter" aria-hidden="true" />

          <header className={`collage-title ${styles.title}`}>
            <p className="collage-eyebrow">{FARM_STORY.weekday} <span>·</span> {FARM_STORY.year}</p>
            <Editable id="title" as="h1" value={FARM_STORY.date} {...editProps} />
            <Editable id="subtitle" className="collage-subtitle" value={`${FARM_STORY.subtitle}.`} {...editProps} />
            <Editable id="keywords" value={FARM_STORY.keywords.join(" / ")} className="collage-keywords" {...editProps} />
          </header>

          {FARM_ELEMENTS.map((el, index) => <figure key={el.id}
            className={`collage-el collage-el--${el.frame === "photo" ? "photo" : el.frame}`}
            style={{ ...place(el), animationDelay: `${0.1 + index * 0.1}s` }} {...hover(el.id)} tabIndex={0}
            onFocus={() => setFocus(el.id)} onBlur={() => setFocus(null)} aria-label={el.provenance.label}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={el.src} alt={el.alt} draggable={false} style={{ objectFit: el.fit ?? "cover" }} />
            {el.frame === "photo" && el.tape && <span className={`collage-tape collage-tape--${el.tape} collage-tape--${el.tapeAt}`} aria-hidden="true" />}
            {el.frame === "photo" && <figcaption>{el.time}</figcaption>}
          </figure>)}

          {FARM_TEXT.map((item) => <div key={item.id} className={`collage-words ${styles.words}`}
            style={{ left: item.x, top: item.y, width: item.w }} {...hover(item.id)}>
            <Editable id={item.id} value={item.text} {...editProps} onFocus={() => setFocus(item.id)} onBlur={() => setFocus(null)} />
          </div>)}

          <svg className={`collage-ink ${styles.ink}`} viewBox={`0 0 ${FARM_CANVAS.width} ${FARM_CANVAS.height}`} aria-hidden="true">
            <path d="M745 246 q 19 -25 40 -3 q -11 22 -38 33 q -29 -17 -30 -38 q 22 -19 28 8" />
            <path className={styles.sage} d="M904 905 q -24 -28 -45 -2 q 22 1 23 25 M859 903 q 31 -43 58 -39" />
          </svg>
          <p className={`${styles.label} ${styles.labelPuppies}`}>puppy pile!</p>
          <p className={`${styles.label} ${styles.labelMatcha}`}>matcha after</p>

          <span className="collage-folio collage-folio--left" aria-hidden="true">i</span>
          <span className="collage-folio collage-folio--right" aria-hidden="true">ii</span>
        </article>
      </div>
    </div>
    <p className="collage-source" role="status" aria-live="polite">
      {active ? <><b>{active.label}</b><span className={`treatment treatment--${active.treatment.toLowerCase()}`}>{TREATMENT_LABEL[active.treatment]}</span><span className="collage-source-detail">{active.detail}</span></>
        : <span className="collage-source-hint">Hover to see where anything came from · click any words to edit them</span>}
    </p>
  </div>;
}
