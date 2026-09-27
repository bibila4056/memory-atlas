import { test, expect } from "@playwright/test";

test("calendar: tab from Capture, the day is stamped with its own art, click opens that memory", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.addInitScript(() => sessionStorage.setItem("memory-atlas.diary-opened", "true"));
  await page.goto("/");
  await page.getByRole("link", { name: "Calendar" }).click();
  await expect(page).toHaveURL(/\/memories$/);
  await expect(page.getByRole("heading", { name: "September 2026" })).toBeVisible();
  const day = page.getByRole("gridcell", { name: /Saturday, September 12/ });
  // Hero = the hand-cut skill art (largest); stickers used that day are smaller accents.
  await expect(day.locator(".stamp-hero")).toHaveAttribute("src", "/memories/rainy-day/churros-cutout.png");
  const hero = (await day.locator(".stamp-hero").boundingBox())!;
  for (const sticker of await day.locator(".stamp-sticker").all()) expect((await sticker.boundingBox())!.width).toBeLessThan(hero.width);
  await expect(page.getByRole("gridcell", { name: /Open this memory/ })).toHaveCount(1);
  await day.click();
  await expect(page).toHaveURL(/\/memories\/rainy-day/);
  await expect(page.getByRole("article", { name: /Memory spread/ })).toBeVisible();
  expect(errors).toEqual([]);
});
