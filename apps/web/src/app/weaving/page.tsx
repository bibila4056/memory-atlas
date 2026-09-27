import { VoiceTranscript } from "@/components/voice-transcript";
import Link from "next/link";
import type { CaptureSession } from "@/lib/capture";

export const dynamic = "force-dynamic";
export default async function WeavingEntry({ searchParams }: { searchParams: Promise<{ session?: string }> }) {
  const { session: id } = await searchParams;
  let session: CaptureSession | null = null;
  if (id && /^[0-9a-f-]{36}$/i.test(id)) {
    const origin = process.env.MEMORY_ATLAS_API_URL ?? "http://127.0.0.1:8000";
    const response = await fetch(`${origin}/api/session/${id}`, { cache: "no-store", signal: AbortSignal.timeout(8000) });
    if (response.ok) session = await response.json();
  }
  return <main className="weaving-entry"><Link href="/" className="text-link">← Back to your notebook</Link><section>
    <p className="page-eyebrow">Your memory begins here</p>
    <h1>{session?.fragments.length ? "Ready to weave." : "Start with a little of your day."}</h1>
    <p>{session?.fragments.length ? `${session.fragments.length} fragments gathered. Your originals are safely kept.` : "Add your photos, words, or voice in your notebook."}</p>
    {session?.fragments.filter((fragment) => fragment.modality === "audio").map((fragment) => <VoiceTranscript key={fragment.id} fragment={fragment} />)}
    <p className="weaving-checkpoint">Capture is ready. Story weaving is the next step in this preview.</p>
    <Link href="/">Return to Capture</Link>
  </section></main>;
}
