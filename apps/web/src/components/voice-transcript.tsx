"use client";

import { useEffect, useRef, useState } from "react";
import { captureRequest, type SourceFragment } from "@/lib/capture";
import type { components } from "@/lib/api-schema";

type Transcript = components["schemas"]["SourceTranscript"];
type Segment = components["schemas"]["TranscriptSegment"];

function clock(ms: number) {
  return `${Math.floor(ms / 60000)}:${(ms / 1000 % 60).toFixed(1).padStart(4, "0")}`;
}

export function VoiceTranscript({ fragment }: { fragment: SourceFragment }) {
  const [transcript, setTranscript] = useState<Transcript | null>(fragment.transcript ?? null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(!fragment.transcript);
  const [playing, setPlaying] = useState<number | null>(null);
  const [loadingClip, setLoadingClip] = useState<number | null>(null);
  const request = useRef<Promise<Transcript> | null>(null);
  const context = useRef<AudioContext | null>(null);
  const buffer = useRef<AudioBuffer | null>(null);
  const player = useRef<AudioBufferSourceNode | null>(null);
  const revision = useRef(0);

  function transcribe() {
    request.current ??= captureRequest<Transcript>("/api/transcribe", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source_id: fragment.id }),
    });
    return request.current;
  }
  useEffect(() => {
    if (fragment.transcript) return;
    let active = true;
    transcribe().then((result) => { if (active) setTranscript(result); })
      .catch((error) => { if (active) setError(error instanceof Error ? error.message : "Couldn’t transcribe your recording."); })
      .finally(() => { if (active) setPending(false); });
    return () => { active = false; };
    // This component is keyed by stable source ID; one request also survives Strict Mode replay.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fragment.id]);
  useEffect(() => () => {
    revision.current++;
    player.current?.stop();
    void context.current?.close();
    context.current = null;
  }, []);

  async function retry() {
    request.current = null; setError(""); setPending(true);
    try { setTranscript(await transcribe()); }
    catch (error) { setError(error instanceof Error ? error.message : "Couldn’t transcribe your recording."); }
    finally { setPending(false); }
  }
  async function play(segment: Segment, index: number) {
    const current = ++revision.current;
    player.current?.stop(); player.current = null;
    if (playing === index) { setPlaying(null); setLoadingClip(null); return; }
    setPlaying(null); setLoadingClip(index); setError("");
    try {
      context.current ??= new AudioContext();
      const audio = context.current;
      await audio.resume();
      if (!buffer.current) {
        const response = await fetch(fragment.original_media_ref!);
        if (!response.ok) throw new Error("Couldn’t load the original recording.");
        buffer.current = await audio.decodeAudioData(await response.arrayBuffer());
      }
      if (current !== revision.current) return;
      const start = segment.clip_start_ms / 1000, end = segment.clip_end_ms / 1000;
      if (start < 0 || end <= start || end > buffer.current.duration) throw new Error("This excerpt’s timestamps fall outside the original recording.");
      const source = audio.createBufferSource();
      source.buffer = buffer.current; source.connect(audio.destination);
      source.onended = () => { source.disconnect(); if (current === revision.current) { setPlaying(null); player.current = null; } };
      player.current = source;
      // Audio-clock scheduling bounds playback to the original range without polling timers.
      source.start(0, start, end - start);
      setPlaying(index);
    } catch (error) { if (current === revision.current) setError(error instanceof Error ? error.message : "This browser couldn’t play the original clip."); }
    finally { if (current === revision.current) setLoadingClip(null); }
  }

  return <div className="voice-transcript" aria-label="Voice transcript" data-voice-source={fragment.id}>
    <h2>In your voice.</h2>
    <p className="transcript-intro">Listen to the original moment behind each excerpt.</p>
    {pending && <p role="status">Listening to your recording…</p>}
    {error && <p role="alert">{error} {!transcript && <button className="text-link" disabled={pending} onClick={retry}>Retry transcription</button>}</p>}
    {transcript?.segments.length === 0 && <p>No spoken words were detected. Your original recording is kept.</p>}
    {transcript?.segments.map((segment, index) => <div className="transcript-excerpt" key={`${segment.clip_start_ms}-${segment.clip_end_ms}`}>
      <blockquote>{segment.text}</blockquote>
      <button type="button" aria-label={`${playing === index ? "Stop" : "Play"} original excerpt ${index + 1}`} aria-pressed={playing === index} onClick={() => play(segment, index)}>
        <span aria-hidden="true">{playing === index ? "Ⅱ" : "▷"}</span> {loadingClip === index ? "Loading original…" : playing === index ? "Stop excerpt" : "Hear original"}
        <time>{clock(segment.clip_start_ms)} – {clock(segment.clip_end_ms)}</time>
      </button>
    </div>)}
  </div>;
}
