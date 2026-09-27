import { WeavingProgress } from "@/components/weaving-progress";

export const metadata = { title: "Memory Atlas — Weaving" };

export default async function WeavePage({ searchParams }: { searchParams: Promise<{ session?: string; t?: string }> }) {
  const { session, t } = await searchParams;
  const id = session && /^[0-9a-f-]{36}$/i.test(session) ? session : undefined;
  // ?t=<seconds> sets the run length for rehearsals; the demo default is a slow, believable pace.
  const seconds = Math.min(600, Math.max(5, Number(t) || 150));
  return <WeavingProgress sessionId={id} seconds={seconds} />;
}
