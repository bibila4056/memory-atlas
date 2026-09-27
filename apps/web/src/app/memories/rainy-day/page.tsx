import Link from "next/link";
import { RainyDaySpread } from "@/components/rainy-day-spread";

export const metadata = { title: "Memory Atlas — September 12" };

export default async function RainyDayMemory({ searchParams }: { searchParams: Promise<{ session?: string }> }) {
  const { session } = await searchParams;
  const id = session && /^[0-9a-f-]{36}$/i.test(session) ? session : undefined;
  return <main className="memory-page">
    <header className="capture-masthead">
      <Link href="/" className="wordmark">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className="wordmark-sprig" src="/illustrations/mark.png" alt="" aria-hidden="true" />
        Memory Atlas</Link>
      <nav className="memory-nav" aria-label="Notebook">
        <Link href="/">Capture</Link>
        <Link href="/memories">Calendar</Link>
      </nav>
    </header>
    <RainyDaySpread sessionId={id} />
  </main>;
}
