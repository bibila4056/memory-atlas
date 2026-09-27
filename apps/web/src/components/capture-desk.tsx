"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { captureRequest, ingestFragments, restoreSession, type CaptureSession, type SourceFragment } from "@/lib/capture";
import { CaptureIcon } from "./capture-icons";
import { PhotoInspector } from "./photo-inspector";
import { VoiceCapture } from "./voice-capture";

export function CaptureDesk() {
  const router = useRouter();
  const [session, setSession] = useState<CaptureSession | null>(null);
  const [draft, setDraft] = useState("");
  const [uploading, setUploading] = useState(false);
  const [pending, setPending] = useState<Set<string>>(new Set());
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [voiceOpen, setVoiceOpen] = useState(false);
  const [textOpen, setTextOpen] = useState(false);
  const [guideOpen, setGuideOpen] = useState(false);
  const [guide, setGuide] = useState("");
  const [dragging, setDragging] = useState(false);
  const textInput = useRef<HTMLTextAreaElement>(null);
  const photosInput = useRef<HTMLInputElement>(null);
  const voiceInput = useRef<HTMLInputElement>(null);
  const uploadLock = useRef(false);
  useEffect(() => {
    let active = true;
    restoreSession().then((saved) => {
      if (!active) return;
      setSession(saved);
      setGuide(saved.weave_instruction ?? "");
      const kept = localStorage.getItem(`memory-atlas.draft.${saved.session_id}`) ?? "";
      if (kept) { setDraft(kept); setTextOpen(true); }
    }).catch((error) => { if (active) setError(error instanceof Error ? error.message : "Couldn’t open your notebook."); });
    return () => { active = false; };
  }, []);
  useEffect(() => { if (textOpen) textInput.current?.focus(); }, [textOpen]);
  const selectedFragment = session?.fragments.find((fragment) => fragment.id === selected);
  const replace = (fragment: SourceFragment) => setSession((current) => current && ({ ...current, fragments: current.fragments.map((item) => item.id === fragment.id ? fragment : item) }));
  const mark = (id: string, on: boolean) => setPending((current) => { const next = new Set(current); if (on) next.add(id); else next.delete(id); return next; });

  /** Per-card change: optimistic, never disables the rest of the page (that was the flicker). */
  async function setKeep(fragment: SourceFragment, keepOriginal: boolean) {
    setError(""); replace({ ...fragment, keep_original: keepOriginal });
    try {
      replace(await captureRequest<SourceFragment>(`/api/source/${fragment.id}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ keep_original: keepOriginal, source_instruction: fragment.source_instruction ?? null }),
      }));
    } catch (error) { replace(fragment); setError(error instanceof Error ? error.message : "Couldn’t save that change. Please try again."); }
  }
  async function remove(fragment: SourceFragment) {
    mark(fragment.id, true); setError("");
    try { setSession(await captureRequest<CaptureSession>(`/api/source/${fragment.id}`, { method: "DELETE" })); }
    catch (error) { setError(error instanceof Error ? error.message : "Couldn’t delete that. Please try again."); }
    finally { mark(fragment.id, false); }
  }
  async function editNote(fragment: SourceFragment, text: string) {
    if (!text.trim() || text === fragment.original_text) return;
    const before = fragment; replace({ ...fragment, original_text: text });
    try { replace(await captureRequest<SourceFragment>(`/api/source/${fragment.id}/text`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) })); }
    catch (error) { replace(before); setError(error instanceof Error ? error.message : "Couldn’t save your edit."); }
  }
  async function transcribe(fragment: SourceFragment) {
    mark(fragment.id, true); setError("");
    try {
      const transcript = await captureRequest<NonNullable<SourceFragment["transcript"]>>("/api/transcribe", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source_id: fragment.id }) });
      replace({ ...fragment, keep_original: false, transcript });
    } catch (error) { setError(error instanceof Error ? error.message : "Transcription couldn’t finish. Your recording is kept."); }
    finally { mark(fragment.id, false); }
  }
  async function saveGuide() {
    if (!session || guide === (session.weave_instruction ?? "")) return;
    try { setSession(await captureRequest<CaptureSession>(`/api/session/${session.session_id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ weave_instruction: guide }) })); }
    catch (error) { setError(error instanceof Error ? error.message : "Couldn’t save your note to the weaver."); }
  }

  async function addFiles(files: File[]) {
    if (!session) throw new Error("Your notebook is still opening. Please try again.");
    if (uploadLock.current) throw new Error("Still saving the last one. Please retry in a moment.");
    if (!files.length) return;
    uploadLock.current = true; setUploading(true); setError("");
    try { setSession(await ingestFragments(session.session_id, files)); setVoiceOpen(false); }
    catch (error) { setError(error instanceof Error ? error.message : "Couldn’t keep those files. Please try again."); throw error; }
    finally { uploadLock.current = false; setUploading(false); }
  }
  async function saveNote() {
    if (!session || !draft.trim()) return session;
    const updated = await ingestFragments(session.session_id, [], draft);
    setSession(updated); setDraft(""); setTextOpen(false);
    localStorage.removeItem(`memory-atlas.draft.${session.session_id}`);
    return updated;
  }
  async function addNote() {
    if (uploadLock.current) return;
    uploadLock.current = true; setUploading(true); setError("");
    try { await saveNote(); }
    catch (error) { setError(error instanceof Error ? error.message : "Your words couldn’t be saved. Please try again."); }
    finally { uploadLock.current = false; setUploading(false); }
  }
  async function weave() {
    if (!session || uploadLock.current) return;
    uploadLock.current = true; setUploading(true); setError("");
    try {
      await saveGuide();
      const ready = await saveNote();
      if (ready?.fragments.length) router.push(`/weave?session=${ready.session_id}`);
    } catch (error) { setError(error instanceof Error ? error.message : "Please try again."); }
    finally { uploadLock.current = false; setUploading(false); }
  }
  const today = new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
  const count = session?.fragments.length ?? 0;
  const canWeave = !!session && (count > 0 || !!draft.trim());
  let photoNumber = 0;
  return <main className="capture-page">
    {/* Colour-pencil botanicals are renderer chrome: decorative, never source-derived. */}
    {/* eslint-disable-next-line @next/next/no-img-element */}
    <img className="desk-botanical desk-botanical--top" src="/illustrations/sprig-b.png" alt="" aria-hidden="true" />
    {/* eslint-disable-next-line @next/next/no-img-element */}
    <img className="desk-botanical desk-botanical--bottom" src="/illustrations/sprig-a.png" alt="" aria-hidden="true" />
    <header className="capture-masthead"><Link href="/" className="wordmark">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="wordmark-sprig" src="/illustrations/mark.png" alt="" aria-hidden="true" />
      Memory Atlas</Link></header>
    <nav className="notebook-tabs" aria-label="Notebook"><span aria-current="page">Capture</span><Link href="/memories">Calendar</Link></nav>
    <div className="notebook-boards"><section className={`capture-notebook${dragging ? " is-dragging" : ""}`} aria-label="Capture Desk"
      onDragOver={(event) => { event.preventDefault(); if (event.dataTransfer.types.includes("Files")) setDragging(true); }}
      onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false); }}
      onDrop={(event) => { event.preventDefault(); setDragging(false); void addFiles(Array.from(event.dataTransfer.files)).catch(() => {}); }}>
      <div className="capture-paper-grain" aria-hidden="true" />
      <div className="capture-page-left">
        <p className="diary-date" suppressHydrationWarning>{today}</p>
        <h1>What do you want<br />to <em>remember</em> today?</h1>
        <div className="capture-actions" aria-label="Add to your memory">
          <button type="button" disabled={!session || uploading} onClick={() => photosInput.current?.click()}><CaptureIcon kind="photo" /><span>Photos</span></button>
          <button type="button" disabled={!session} aria-pressed={voiceOpen} onClick={() => { setVoiceOpen(true); setTextOpen(false); }}><CaptureIcon kind="voice" /><span>Voice</span></button>
          <button type="button" disabled={!session} aria-pressed={textOpen} onClick={() => { setTextOpen(true); setVoiceOpen(false); }}><CaptureIcon kind="text" /><span>Text</span></button>
        </div>
        <input className="sr-only" type="file" accept="image/jpeg,image/png,image/webp,image/gif,image/avif" multiple ref={photosInput} aria-label="Choose photos" onChange={(event) => { void addFiles(Array.from(event.target.files ?? [])).catch(() => {}); event.target.value = ""; }} />
        <input className="sr-only" type="file" accept="audio/*" ref={voiceInput} aria-label="Choose voice recording" onChange={(event) => { void addFiles(Array.from(event.target.files ?? [])).catch(() => {}); event.target.value = ""; }} />
        {textOpen && <div className="capture-composer">
          <label className="sr-only" htmlFor="memory-note">Your words</label>
          <textarea id="memory-note" ref={textInput} value={draft} maxLength={20000} disabled={!session}
            onKeyDown={(event) => { if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) void addNote(); if (event.key === "Escape" && !draft) setTextOpen(false); }}
            onChange={(event) => { setDraft(event.target.value); if (session) localStorage.setItem(`memory-atlas.draft.${session.session_id}`, event.target.value); }}
            placeholder="A place, a feeling, a few unfinished thoughts…" />
          <div className="composer-row">
            <button type="button" className="quiet-save" disabled={!draft.trim() || uploading} onClick={addNote}>Add to the page <kbd>⌘ Enter</kbd></button>
            <button type="button" className="text-link" onClick={() => { setTextOpen(false); }}>Close</button>
          </div>
        </div>}
        {voiceOpen && <VoiceCapture onSave={(file) => addFiles([file])} onUpload={() => voiceInput.current?.click()} onClose={() => setVoiceOpen(false)} />}
        <div className="weaver-guide">
          {guideOpen || guide ? <>
            <label htmlFor="weaver-guide">For the weaver</label>
            <textarea id="weaver-guide" rows={2} value={guide} maxLength={2000} placeholder="Anything it should know? e.g. “Make it about Shelly.”"
              onChange={(event) => setGuide(event.target.value)} onBlur={() => void saveGuide()} />
          </> : <button type="button" className="text-link" onClick={() => setGuideOpen(true)}>+ Tell the weaver something</button>}
        </div>
        <div className="capture-submit-row"><button type="button" className="weave-button" disabled={!canWeave || uploading || voiceOpen} onClick={weave}>Weave this memory <CaptureIcon kind="arrow" /></button></div>
        <p className="capture-status" role="status">{uploading ? "Saving…" : !session && !error ? "Opening your notebook…" : ""}</p>
        {error && <div className="capture-error" role="alert"><p>{error}</p>{!session && <button type="button" onClick={() => location.reload()}>Try again</button>}</div>}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className="pressed-flower" src="/illustrations/pressed-flower.png" alt="" aria-hidden="true" />
        <span className="pressed-flower-tape" aria-hidden="true" />
      </div>
      <div className="capture-page-right">
        <p className="fragments-count">{count ? <><b>{count}</b> {count === 1 ? "fragment" : "fragments"} collected here</> : "Nothing collected yet"}</p>
        {!count && <div className="empty-fragments"><div className="empty-paper-stack" aria-hidden="true"><div /><div /></div><p>Little pieces of your day.</p><span>Drop photos here, or add a few words.</span></div>}
        <div className="fragment-collection">
          {session?.fragments.map((fragment) => {
            const label = fragment.modality === "image" ? `Photo ${++photoNumber}` : fragment.modality === "text" ? "Your words" : "Your voice";
            const busy = pending.has(fragment.id);
            return <article className={`captured-fragment captured-fragment--${fragment.modality}`} key={fragment.id} data-source-id={fragment.id} aria-busy={busy || undefined}>
              {fragment.modality === "image" && fragment.original_media_ref && <button type="button" className="inspect-photo" aria-label={`Inspect ${fragment.filename ?? "photo"}`} onClick={() => setSelected(fragment.id)}><Image src={fragment.original_media_ref} alt={fragment.filename ?? label} width={220} height={180} unoptimized style={{ objectFit: "contain" }} /></button>}
              {fragment.modality === "text" && <EditableNote text={fragment.original_text ?? ""} onSave={(text) => void editNote(fragment, text)} />}
              {fragment.modality === "audio" && <>
                <VoiceNote src={fragment.original_media_ref ?? undefined} />
                {!fragment.keep_original && <p className="voice-heard" aria-live="polite">{busy ? "Listening and writing it down…" : fragment.transcript ? fragment.transcript.segments.map((s) => s.text.trim()).join(" ") || "(no words heard)" : <button type="button" className="text-link" onClick={() => void transcribe(fragment)}>Write it down</button>}</p>}
              </>}
              {fragment.modality !== "audio" && <span className="tape" aria-hidden="true" />}
              <button type="button" className="delete-fragment" aria-label={`Delete ${fragment.filename ?? label}`} disabled={busy} onClick={() => void remove(fragment)}>×</button>
              <footer><span className="fragment-label">{label}</span>
                <Choice name={fragment.id} value={fragment.keep_original} disabled={busy}
                  onChange={(keep) => { void setKeep(fragment, keep); if (fragment.modality === "audio" && !keep && !fragment.transcript) void transcribe(fragment); }}
                  options={fragment.modality === "image" ? ["Keep original", "Make it art"] : fragment.modality === "text" ? ["As I wrote it", "Polish with AI"] : ["Play my voice", "Turn into words"]} />
              </footer>
            </article>;
          })}
        </div>
        {selectedFragment && <PhotoInspector fragment={selectedFragment} onClose={() => setSelected(null)} />}
      </div>
    </section></div>
  </main>;
}

/** A note card you can click to revise. ⌘↵ or clicking away saves; Esc cancels. */
function EditableNote({ text, onSave }: { text: string; onSave: (text: string) => void }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(text);
  const box = useRef<HTMLTextAreaElement>(null);
  useEffect(() => { if (editing) { box.current?.focus(); box.current?.setSelectionRange(value.length, value.length); } }, [editing]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!editing) return <p className="captured-note" role="button" tabIndex={0} title="Click to edit"
    onClick={() => { setValue(text); setEditing(true); }} onKeyDown={(event) => { if (event.key === "Enter") { setValue(text); setEditing(true); } }}>{text}</p>;
  return <textarea ref={box} className="captured-note captured-note--editing" aria-label="Edit your words" value={value} rows={Math.min(8, Math.max(2, Math.ceil(value.length / 48)))}
    onChange={(event) => setValue(event.target.value)} onBlur={() => { setEditing(false); onSave(value); }}
    onKeyDown={(event) => { if (event.key === "Escape") { setValue(text); setEditing(false); } if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) { setEditing(false); onSave(value); } }} />;
}

/** Two-way choice for words and voice. `true` keeps the original as the thing shown on the page. */
function Choice({ name, value, options, disabled, onChange }: { name: string; value: boolean; options: [string, string]; disabled: boolean; onChange: (keep: boolean) => void }) {
  return <span className="choice" role="radiogroup" aria-label="How this appears in your memory">
    {options.map((label, i) => <label key={label} data-on={value === (i === 0) || undefined}>
      <input type="radio" name={`choice-${name}`} checked={value === (i === 0)} disabled={disabled} onChange={() => onChange(i === 0)} />{label}
    </label>)}
  </span>;
}

function VoiceNote({ src }: { src?: string }) {
  const audio = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState({ at: 0, of: 0 });
  const fmt = (t: number) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}`;
  return <div className="voice-note">
    <button type="button" className="voice-play" aria-label={playing ? "Pause voice note" : "Play voice note"} onClick={() => { const el = audio.current; if (el) { if (el.paused) void el.play(); else el.pause(); } }}>{playing ? "❚❚" : "▶"}</button>
    <span className="voice-bars" aria-hidden="true">{Array.from({ length: 34 }, (_, i) => <i key={i} data-on={time.of ? i / 34 < time.at / time.of : undefined} style={{ height: 5 + ((i * 53) % 19) }} />)}</span>
    <span className="voice-time">{fmt(time.at)}{time.of && Number.isFinite(time.of) ? ` / ${fmt(time.of)}` : ""}</span>
    <audio ref={audio} preload="metadata" src={src} onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onEnded={() => setPlaying(false)}
      onLoadedMetadata={(e) => setTime({ at: 0, of: e.currentTarget.duration })} onTimeUpdate={(e) => setTime({ at: e.currentTarget.currentTime, of: e.currentTarget.duration })} />
  </div>;
}
