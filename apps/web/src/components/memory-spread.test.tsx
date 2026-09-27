import React from "react";
import { render, screen, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import fixture from "../../../api/app/fixtures/resolved_visual_plan.json";
import { MemorySpread } from "./memory-spread";
import { assertRenderable, assertRevision, type ResolvedVisualPlan } from "@/lib/plan";

// Input is the same JSON that the API validates; TypeScript types come from OpenAPI.
const plan: ResolvedVisualPlan = JSON.parse(JSON.stringify(fixture));
afterEach(cleanup);

describe("resolved plan renderer", () => {
  it("renders source-linked text and original media as distinct layers at canonical bounds", () => {
    const { container } = render(<MemorySpread plan={plan} />);
    expect(screen.getByTestId("memory-spread").style.width).toBe("1600px");
    expect(screen.getByTestId("memory-spread").style.height).toBe("1000px");
    for (const element of plan.elements) {
      const node = container.querySelector(`[data-element-id="${element.id}"]`);
      expect(node?.getAttribute("data-source-ids")).toBe("source_ids" in element ? element.source_ids.join(" ") : null);
      if (element.kind === "text") expect(node?.textContent).toBe(element.text);
    }
    expect(screen.getByAltText(/Temporary synthetic sample/).getAttribute("src")).toBe("/demo/flower-market-morning.png");
  });

  it("refuses a draft at runtime, even if it crosses the TypeScript boundary", () => {
    const draft = JSON.parse(JSON.stringify({ ...plan, status: "draft" }));
    expect(() => assertRenderable(draft)).toThrow("Only resolved");
    expect(() => render(<MemorySpread plan={draft} />)).toThrow("Only resolved");
  });

  it("accepts an immutable asset revision but rejects stale, skipped, or moved layouts", () => {
    const next = structuredClone(plan);
    next.plan_revision += 1;
    const asset = next.elements.find((element) => element.kind === "generated_asset")!;
    if (asset.kind !== "generated_asset") throw new Error("Missing test asset");
    asset.asset_ref = "/demo/new-immutable-asset.svg";
    asset.generation_mode = "live";
    expect(() => assertRevision(plan, next)).not.toThrow();
    expect(() => assertRevision(next, plan)).toThrow("Stale");
    expect(() => assertRevision(plan, { ...next, plan_revision: 3 })).toThrow("out-of-order");
    asset.bounds.x += 1;
    expect(() => assertRevision(plan, next)).toThrow("composition");
  });
});
