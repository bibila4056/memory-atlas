import type { components } from "./api-schema";

// These aliases are generated from Pydantic, never a second wire contract.
export type ResolvedVisualPlan = components["schemas"]["ResolvedVisualPlan"];
export type VisualElement = ResolvedVisualPlan["elements"][number];
export type ElementMask = NonNullable<components["schemas"]["PhotoElement"]["mask"]>;

export function assertRenderable(plan: ResolvedVisualPlan): void {
  if (plan.status !== "resolved") throw new Error("Only resolved plans can be rendered.");
  if (plan.canvas.width !== 1600 || plan.canvas.height !== 1000) {
    throw new Error("The spread requires a 1600 × 1000 canvas.");
  }
  if (plan.elements.some((element) => element.kind === "generated_asset" && !element.asset_ref)) {
    throw new Error("Every generated asset must be resolved before rendering.");
  }
}

// Revision handling is bounded to immutable asset replacement (ADR-0005).
export function assertRevision(previous: ResolvedVisualPlan, next: ResolvedVisualPlan): void {
  assertRenderable(next);
  if (previous.plan_id !== next.plan_id) return;
  if (JSON.stringify(previous) === JSON.stringify(next)) return;
  if (next.plan_revision !== previous.plan_revision + 1) {
    throw new Error("Stale or out-of-order plan revision.");
  }
  const layout = (plan: ResolvedVisualPlan) => JSON.stringify({
    ...plan,
    plan_revision: 0,
    elements: plan.elements.map((element) => {
      if (element.kind !== "generated_asset") return element;
      return { ...element, asset_ref: null, generation_mode: null };
    }),
  });
  if (layout(previous) !== layout(next)) throw new Error("Asset resolution cannot change the composition.");
}
