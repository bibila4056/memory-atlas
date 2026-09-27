export function CaptureIcon({ kind }: { kind: "photo" | "voice" | "text" | "arrow" }) {
  const paths = {
    photo: <><rect x="3" y="4" width="18" height="16" rx="1" /><path d="m3 16 5-5 4 4 3-3 6 6" /><circle cx="16" cy="8" r="1" /></>,
    voice: <><rect x="9" y="3" width="6" height="12" rx="3" /><path d="M6 11a6 6 0 0 0 12 0M12 17v4m-3 0h6" /></>,
    text: <><path d="M5 5h14M12 5v15m-4 0h8M5 5v3m14-3v3" /></>,
    arrow: <path d="M4 12h16m-6-6 6 6-6 6" />,
  };
  return <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[kind]}</svg>;
}
