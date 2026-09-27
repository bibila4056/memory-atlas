"use client";

import { useEffect, useRef } from "react";
import type { SourceFragment } from "@/lib/capture";

export function PhotoInspector({ fragment, onClose }: { fragment: SourceFragment; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { const element = dialog.current; element?.showModal(); return () => element?.close(); }, []);
  return <dialog ref={dialog} className="photo-inspector" aria-label="Original photo" onClose={(event) => { if (!event.currentTarget.open) onClose(); }} onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <header><span>{fragment.filename} <small>Fit to screen · original preserved</small></span><button type="button" onClick={onClose} aria-label="Close original photo">×</button></header>
    <div className="original-photo-scroll">
      {/* The original bytes are untouched; only the on-screen presentation is scaled to fit. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={fragment.original_media_ref!} alt={fragment.filename ?? "Original photo"} />
    </div>
  </dialog>;
}
