"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { CaptureSession, SourceFragment } from "@/lib/capture";
import { ANNOTATIONS, AUTHOR_NOTE_ORIGINAL, BASE_ELEMENTS, CANVAS, ELEMENTS as DEFAULT_ELEMENTS, placeStickers, STORY, type Provenance, type SpreadEl } from "@/lib/rainy-day";
import type { WeaveResult } from "@/lib/weave";

const TREATMENT_LABEL: Record<Provenance["treatment"], string> = { PRESERVE: "Preserved", DISTILL: "Distilled", LIBRARY: "From the drawer", AUTHOR: "Your words" };

/** Only presentation changes: fixes spacing/grammar, never adds facts. The original stays one hover away. */
function lightlyPolish(text: string) {
  return text.replace(/\bkinda\b/g, "kind of").replace(/\bgonna\b/g, "going to").replace(/\bluckily the\b/g, "luckily, the").replace(/[ \t]+/g, " ").trim();
}

function useFit(ref: React.RefObject<HTMLDivElement | null>) {
  const [scale, setScale] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => setScale(Math.min(entry.contentRect.width / CANVAS.width, entry.contentRect.height / CANVAS.height)));
    observer.observe(el);
    return () => observer.disconnect();
  }, [ref]);
  return scale;
}

/** Every piece of text on the page can be edited in place; edits are the author's and are kept per memory. */
function useEdits(key: string) {
  const [edits, setEdits] = useState<Record<string, string>>(() => {
    if (typeof window === "undefined") return {};
    try { return JSON.parse(localStorage.getItem(key) ?? "{}"); } catch { return {}; }
  });
  const save = useCallback((id: string, value: string) => setEdits((current) => {
    const next = { ...current, [id]: value };
    try { localStorage.setItem(key, JSON.stringify(next)); } catch { /* private mode: edit lasts for this visit */ }
    return next;
  }), [key]);
  return [edits, save] as const;
}

function Editable({ id, as: Tag = "p", className, value, edits, onSave, onFocus, onBlur }: {
  id: string; as?: "p" | "h1" | "span"; className?: string; value: string; edits: Record<string, string>;
  onSave: (id: string, value: string) => void; onFocus?: () => void; onBlur?: () => void;
}) {
  const shown = edits[id] ?? value;
  return <Tag className={`${className ?? ""} editable`} contentEditable suppressContentEditableWarning suppressHydrationWarning spellCheck={false} data-edited={edits[id] !== undefined && edits[id] !== value || undefined}
    onFocus={onFocus} onBlur={(event) => { const text = event.currentTarget.innerText.trim(); if (text && text !== shown) onSave(id, text); onBlur?.(); }}
    onKeyDown={(event) => { if (event.key === "Escape" || (event.key === "Enter" && Tag !== "p")) { event.preventDefault(); event.currentTarget.blur(); } }}>{shown}</Tag>;
}

function transcriptText(fragment: SourceFragment) {
  return fragment.transcript?.segments.map((s) => s.text.trim()).join(" ").trim() ?? "";
}

export function RainyDaySpread({ sessionId }: { sessionId?: string }) {
  const stage = useRef<HTMLDivElement>(null);
  const scale = useFit(stage);
  const [session, setSession] = useState<CaptureSession | null>(null);
  const [focus, setFocus] = useState<string | null>(null);
  const [playing, setPlaying] = useState<string | null>(null);
  const audios = useRef<Record<string, HTMLAudioElement | null>>({});
  const [edits, saveEdit] = useEdits(`memory-atlas.spread-edits.${sessionId ?? "demo"}`);
  const [weave, setWeave] = useState<WeaveResult | null>(null);
  useEffect(() => {
    if (!sessionId) return;
    let live = true;
    fetch(`/api/session/${sessionId}`).then((r) => (r.ok ? r.json() : null)).then((data) => { if (live) setSession(data); }).catch(() => {});
    fetch(`/api/weave/${sessionId}`).then((r) => (r.ok ? r.json() : null)).then((data) => { if (live) setWeave(data); }).catch(() => {});
    return () => { live = false; };
  }, [sessionId]);
  // One sticker pick for the whole product: the weave's (shown on the Weaving screen) wins over the local fallback.
  const chosenStickers = weave?.stickers.filter((p) => p.chosen);
  const ELEMENTS = chosenStickers?.length ? [...BASE_ELEMENTS, ...placeStickers(chosenStickers)] : DEFAULT_ELEMENTS;

  const notes = session?.fragments.filter((f) => f.modality === "text") ?? [];
  const voices = session?.fragments.filter((f) => f.modality === "audio") ?? [];
  const spoken = voices.find((v) => !v.keep_original && transcriptText(v));   // "Turn into words" → a quote on the page
  const kept = voices.find((v) => v.keep_original);                           // "Play my voice" → a playable chip
  const refined = notes.some((n) => !n.keep_original);
  const original = notes.length ? notes.map((n) => n.original_text ?? "").join("\n\n") : AUTHOR_NOTE_ORIGINAL;
  const words = notes.length ? notes.map((n) => (n.keep_original ? n.original_text ?? "" : lightlyPolish(n.original_text ?? ""))).join("\n\n") : AUTHOR_NOTE_ORIGINAL;

  const provenance: Record<string, Provenance> = Object.fromEntries(ELEMENTS.map((el) => [el.id, el.provenance]));
  const edited = (id: string) => (edits[id] !== undefined ? " · edited by you on the page" : "");
  provenance.words = { label: "Your note", treatment: "AUTHOR", detail: (refined ? `Lightly polished with your permission · original: “${original}”` : "Exactly as you wrote it") + edited("words") };
  provenance.quote = { label: "Said out loud", treatment: "AUTHOR", detail: "Transcribed word for word from your voice note · press ▶ to hear it" + edited("quote") };
  provenance.voice = { label: "Voice note", treatment: "PRESERVE", detail: "Your original recording, played back as is" };
  const active = focus ? provenance[focus] : null;

  const hover = (id: string) => ({ onMouseEnter: () => setFocus(id), onMouseLeave: () => setFocus(null), "data-focus": focus === id || undefined });
  const place = (el: { x: number; y: number; w: number; h: number; r?: number; z?: number }) => ({ left: el.x, top: el.y, width: el.w, height: el.h, zIndex: el.z ?? 1, "--r": `${el.r ?? 0}deg` } as React.CSSProperties);
  const toggle = (id: string) => {
    const el = audios.current[id];
    if (!el) return;
    Object.entries(audios.current).forEach(([other, a]) => { if (other !== id) a?.pause(); });
    if (el.paused) void el.play(); else el.pause();
  };
  const editProps = { edits, onSave: saveEdit };

  return <div className="collage-wrap">
    <div className="collage-stage" ref={stage}>
      <div className="collage-frame" style={{ width: CANVAS.width * scale, height: CANVAS.height * scale, visibility: scale ? "visible" : "hidden" }}>
        <article className={`collage${focus ? " is-inspecting" : ""}`} aria-label={`Memory spread: ${STORY.weekday}, ${STORY.date}`}
          style={{ width: CANVAS.width, height: CANVAS.height, transform: `scale(${scale})` }}>
          <div className="collage-page collage-page--left" aria-hidden="true" />
          <div className="collage-page collage-page--right" aria-hidden="true" />
          <div className="collage-gutter" aria-hidden="true" />

          {/* Title: the date is the headline; keywords are typed like a label strip. All editable. */}
          <header className="collage-title">
            <p className="collage-eyebrow">{STORY.weekday} <span>·</span> {STORY.year}</p>
            <Editable id="title" as="h1" value={STORY.date} {...editProps} />
            <Editable id="subtitle" className="collage-subtitle" value={`${STORY.subtitle}.`} {...editProps} />
            <Editable id="keywords" className="collage-keywords" value={STORY.keywords.join(" / ")} {...editProps} />
          </header>

          {ELEMENTS.map((el: SpreadEl, index) => <figure key={el.id} className={`collage-el collage-el--${el.kind}${el.kind === "art" ? ` collage-el--${el.frame}` : ""}`}
            style={{ ...place(el), animationDelay: `${0.15 + index * 0.12}s` }} {...hover(el.id)} tabIndex={0} onFocus={() => setFocus(el.id)} onBlur={() => setFocus(null)} aria-label={el.provenance.label}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={el.src} alt={el.alt} draggable={false} />
            {el.kind === "photo" && el.tape && <span className={`collage-tape collage-tape--${el.tape} collage-tape--${el.tapeAt}`} aria-hidden="true" />}
            {el.kind === "photo" && <figcaption>{el.time}</figcaption>}
          </figure>)}

          {/* Pencil marks: rain under the cloud, a few thinking doodles in the margins, and the arrows. */}
          <svg className="collage-ink" viewBox={`0 0 ${CANVAS.width} ${CANVAS.height}`} aria-hidden="true">
            <g className="rain-strokes">
              {[[560, 168], [586, 180], [612, 166], [640, 184], [668, 170], [694, 182], [575, 204], [626, 208], [654, 200]].map(([x, y], i) =>
                <path key={i} d={`M${x} ${y} l -7 16`} />)}
            </g>
            <g className="margin-doodles">
              <path d="M1222 500 l5 11 l12 1 l-9 7 l3 12 l-11 -7 l-10 7 l3 -12 l-9 -7 l12 -1 z" />
              <path d="M760 930 c 8 -10, 22 -6, 20 6 c -2 12, -20 12, -22 0 c -2 -16, 22 -24, 34 -10" />
              <path d="M58 300 m -3 0 a 3 3 0 1 0 6 0 a 3 3 0 1 0 -6 0 M 72 316 m -2 0 a 2 2 0 1 0 4 0 a 2 2 0 1 0 -4 0 M 60 334 m -2.5 0 a 2.5 2.5 0 1 0 5 0 a 2.5 2.5 0 1 0 -5 0" />
              <path d="M1548 930 q -14 -18 -30 -6 q 12 4 10 18 M1520 924 q 20 -30 44 -34" />
            </g>
            {ANNOTATIONS.map((a) => <g key={a.id} className="ink-arrow" data-for={a.target}>
              <path d={a.path} />
              <path d="M0 0 L -13 -7 M0 0 L -13 7" transform={`translate(${a.head.x} ${a.head.y}) rotate(${a.head.angle})`} />
            </g>)}
          </svg>
          {ANNOTATIONS.map((a) => <Editable key={a.id} id={`note-${a.id}`} className="collage-note" value={a.text} {...editProps} />).map((node, i) =>
            <div key={ANNOTATIONS[i].id} className="collage-note-wrap" style={{ left: ANNOTATIONS[i].x, top: ANNOTATIONS[i].y }}>{node}</div>)}

          <div className="collage-words" {...hover("words")}>
            <Editable id="words" value={words} {...editProps} onFocus={() => setFocus("words")} onBlur={() => setFocus(null)} />
            {refined && <span className="collage-words-tag">lightly polished · your original is kept</span>}
          </div>

          {spoken && <div className="collage-quote" {...hover("quote")}>
            <Editable id="quote" value={`“${transcriptText(spoken)}”`} {...editProps} onFocus={() => setFocus("quote")} onBlur={() => setFocus(null)} />
            <button type="button" className="quote-source" onClick={() => toggle(spoken.id)} aria-label={playing === spoken.id ? "Pause the recording" : "Hear this in your voice"}>
              <span aria-hidden="true">{playing === spoken.id ? "❚❚" : "▶"}</span> said out loud
            </button>
            <audio ref={(el) => { audios.current[spoken.id] = el; }} src={spoken.original_media_ref ?? undefined} preload="metadata"
              onPlay={() => setPlaying(spoken.id)} onPause={() => setPlaying(null)} onEnded={() => setPlaying(null)} />
          </div>}

          {kept?.original_media_ref && <div className="collage-voice" {...hover("voice")}>
            <button type="button" onClick={() => toggle(kept.id)} aria-label={playing === kept.id ? "Pause your voice note" : "Play your voice note"}>
              <span className="voice-dot" aria-hidden="true">{playing === kept.id ? "❚❚" : "▶"}</span>
              <span>Hear it in your voice</span>
              <span className="voice-wave" aria-hidden="true">{Array.from({ length: 18 }, (_, i) => <i key={i} style={{ height: 6 + ((i * 37) % 17) }} />)}</span>
            </button>
            <audio ref={(el) => { audios.current[kept.id] = el; }} src={kept.original_media_ref} preload="metadata"
              onPlay={() => setPlaying(kept.id)} onPause={() => setPlaying(null)} onEnded={() => setPlaying(null)} />
          </div>}

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
