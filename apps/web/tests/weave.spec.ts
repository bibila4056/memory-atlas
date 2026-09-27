import { test, expect } from "@playwright/test";
const MAX_STICKERS = 4; // docs/ART_DIRECTION.md §E: up to 2 per page

test("weaving screen progresses, then opens the rainy-day spread with bounded stickers", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/weave?t=5");
  const bar = page.getByRole("progressbar", { name: "Weaving progress" });
  await expect(bar).toBeVisible();
  await page.getByRole("link", { name: "Open your memory" }).click({ timeout: 15000 });
  await expect(page).toHaveURL(/\/memories\/rainy-day/);
  await expect(page.getByRole("article", { name: /Memory spread: Saturday, September 12/ })).toBeVisible();
  expect(await page.locator(".collage-el--sticker").count()).toBeLessThanOrEqual(MAX_STICKERS);
  await page.getByRole("figure", { name: "Tape collage" }).hover();
  await expect(page.getByRole("status")).toContainText("Distilled");
  expect(errors).toEqual([]);
});
