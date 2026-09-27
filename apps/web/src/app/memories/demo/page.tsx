import { SpreadViewer } from "@/components/spread-viewer";
import { getDemoPlan } from "@/lib/api";

export const dynamic = "force-dynamic";
export const metadata = { title: "Memory Atlas — Spread study" };

export default async function DemoMemoryPage() {
  const plan = await getDemoPlan();
  return (
    <main className="study-page">
      <header className="masthead">
        <div className="wordmark">
          <svg width="26" height="24" viewBox="0 0 26 24" fill="none" aria-hidden="true">
            <path d="M13 5C9 2 5 3 2 3v16c4-1 7 0 11 2 4-2 7-3 11-2V3c-3 0-7-1-11 2Zm0 0v16" stroke="currentColor" strokeWidth="1.1" />
          </svg>
          <span>Memory Atlas</span>
        </div>
        <span className="study-label">Spread study <span> / </span> 01</span>
      </header>
      <h1 className="sr-only">Memory Atlas composition study</h1>
      <SpreadViewer plan={plan} />
    </main>
  );
}
