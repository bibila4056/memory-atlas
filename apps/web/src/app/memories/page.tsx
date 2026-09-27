import Link from "next/link";
import { MemoryCalendar } from "@/components/memory-calendar";

export const metadata = { title: "Memory Atlas — Calendar" };

export default function CalendarPage() {
  return <main className="capture-page">
    {/* eslint-disable-next-line @next/next/no-img-element */}
    <img className="desk-botanical desk-botanical--bottom" src="/illustrations/sprig-a.png" alt="" aria-hidden="true" />
    <header className="capture-masthead"><Link href="/" className="wordmark">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="wordmark-sprig" src="/illustrations/mark.png" alt="" aria-hidden="true" />
      Memory Atlas</Link></header>
    <nav className="notebook-tabs" aria-label="Notebook"><Link href="/">Capture</Link><span aria-current="page">Calendar</span></nav>
    <MemoryCalendar />
  </main>;
}
