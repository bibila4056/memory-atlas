"use client";

import { useEffect, useRef, useState } from "react";

export function VoiceCapture({ onSave, onUpload, onClose }: { onSave: (file: File) => Promise<void>; onUpload: () => void; onClose: () => void }) {
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const disposed = useRef(false);
  const [phase, setPhase] = useState<"ready" | "requesting" | "recording" | "saving">("ready");
  const [error, setError] = useState("");
  const [pending, setPending] = useState<File | null>(null);
  useEffect(() => {
    disposed.current = false;
    return () => {
      disposed.current = true;
      if (recorder.current?.state === "recording") { recorder.current.onstop = null; recorder.current.stop(); }
      stream.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);
  async function save(file: File) {
    setPending(file); setPhase("saving"); setError("");
    try { await onSave(file); }
    catch (error) { setError(error instanceof Error ? error.message : "Your clip couldn’t be saved. Retry to keep this recording."); setPhase("ready"); }
  }
  async function start() {
    setError(""); setPhase("requesting");
    try {
      const media = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (disposed.current) { media.getTracks().forEach((track) => track.stop()); return; }
      stream.current = media;
      const recording = new MediaRecorder(media);
      recorder.current = recording;
      const chunks: Blob[] = [];
      recording.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
      recording.onstop = async () => {
        media.getTracks().forEach((track) => track.stop());
        const type = recording.mimeType || "audio/webm";
        await save(new File(chunks, type.includes("mp4") ? "Voice note.m4a" : "Voice note.webm", { type }));
      };
      recording.start(); setPhase("recording");
    } catch { stream.current?.getTracks().forEach((track) => track.stop()); setError("Microphone access isn’t available. You can upload a voice clip instead."); setPhase("ready"); }
  }
  return <section className="voice-capture" aria-label="Add a voice note">
    <div className="preferences-heading"><h3>A few words, in your voice.</h3><button type="button" onClick={onClose} disabled={phase === "saving"} aria-label="Close voice recording">×</button></div>
    <p role="status">{phase === "recording" ? "Recording… Take your time." : phase === "saving" ? "Keeping your original recording…" : "A short voice note is enough."}</p>
    {error && <p role="alert">{error}</p>}
    {phase === "recording" ? <button className="quiet-save" onClick={() => recorder.current?.stop()}>Stop & save</button>
      : <button className="quiet-save" disabled={phase !== "ready"} onClick={() => pending ? save(pending) : start()}>{phase === "requesting" ? "Waiting for microphone…" : phase === "saving" ? "Saving…" : pending ? "Retry saving recording" : "Start recording"}</button>}
    <button className="text-link" onClick={onUpload} disabled={phase !== "ready" || !!pending}>Upload a voice clip</button>
  </section>;
}
