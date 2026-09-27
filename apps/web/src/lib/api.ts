import { assertRenderable, type ResolvedVisualPlan } from "./plan";

export async function getDemoPlan(): Promise<ResolvedVisualPlan> {
  const origin = process.env.MEMORY_ATLAS_API_URL ?? "http://127.0.0.1:8000";
  const response = await fetch(`${origin}/api/plans/demo`, {
    cache: "no-store",
    signal: AbortSignal.timeout(8000),
  });
  if (!response.ok) throw new Error(`Plan request failed (${response.status}).`);
  // FastAPI validates the response with the canonical Pydantic model.
  const plan: ResolvedVisualPlan = await response.json();
  assertRenderable(plan);
  return plan;
}
