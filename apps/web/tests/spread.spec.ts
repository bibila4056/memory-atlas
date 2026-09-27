import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import type { ResolvedVisualPlan } from "../src/lib/plan";

test("real API → public route preserves layers and geometry at desktop sizes and zoom", async ({ page, request }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const response = await request.get("http://127.0.0.1:8000/api/plans/demo");
  expect(response.ok()).toBeTruthy();
  const plan: ResolvedVisualPlan = await response.json();
  let desktopGeometry: number[][] | undefined;
  for (const size of [{ name: "desktop", width: 1440, height: 1000 }, { name: "laptop", width: 1280, height: 800 }]) {
    await page.setViewportSize(size);
    await page.goto("/memories/demo");
    const spread = page.getByTestId("memory-spread");
    await expect(spread).toBeVisible();
    await expect(spread).toHaveAttribute("data-plan-id", plan.plan_id);
    for (const element of plan.elements) {
      const node = page.locator(`[data-element-id="${element.id}"]`);
      await expect(node).toHaveCSS("left", `${element.bounds.x}px`);
      if (element.kind === "text") expect(await node.textContent()).toBe(element.text);
      if ("source_ids" in element) await expect(node).toHaveAttribute("data-source-ids", element.source_ids.join(" "));
    }
    await expect(page.getByAltText(/Temporary synthetic sample/)).toBeVisible();
    const metrics = await spread.evaluate((element) => {
      const canvas = element.getBoundingClientRect();
      return {
        width: canvas.width,
        geometry: Array.from(element.querySelectorAll('[data-element-id]')).map((child) => {
          const rect = child.getBoundingClientRect();
          return [(rect.x - canvas.x) / canvas.width, (rect.y - canvas.y) / canvas.height, rect.width / canvas.width, rect.height / canvas.height];
        }),
      };
    });
    expect(metrics.width).toBeLessThanOrEqual(size.width);
    if (desktopGeometry) {
      metrics.geometry.forEach((bounds, index) => bounds.forEach((value, axis) => expect(value).toBeCloseTo(desktopGeometry![index][axis], 5)));
    } else desktopGeometry = metrics.geometry;
    await page.screenshot({ path: `../../artifacts/issue-2/${size.name}.png`, fullPage: true });
  }
  await page.getByRole("button", { name: "Actual size", exact: true }).click();
  await expect(page.getByTestId("memory-spread")).toHaveCSS("width", "1600px");
  const viewport = page.getByTestId("spread-viewport");
  expect(await viewport.evaluate((element) => element.scrollWidth)).toBeGreaterThanOrEqual(1600);
  await viewport.evaluate((element) => { element.scrollLeft = 900; });
  expect(await viewport.evaluate((element) => element.scrollLeft)).toBeGreaterThan(0);
  await page.screenshot({ path: "../../artifacts/issue-2/desktop-zoom.png", fullPage: true });
  await page.getByRole("button", { name: "Fit spread" }).click();
  expect((await page.getByTestId("memory-spread").boundingBox())!.width).toBeLessThan(1280);
  const photo = await request.get("/demo/flower-market-morning.png");
  expect(await photo.body()).toEqual(await readFile("public/demo/flower-market-morning.png"));
  expect(errors).toEqual([]);
});
