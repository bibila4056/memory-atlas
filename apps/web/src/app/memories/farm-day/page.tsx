import Link from "next/link";
import { FarmDaySpread } from "@/components/farm-day-spread";

export const metadata = { title: "Memory Atlas — September 6" };

export default function FarmDayMemory() {
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
    <FarmDaySpread />
  </main>;
}
