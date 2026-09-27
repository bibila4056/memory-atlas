import { describe, expect, it } from "vitest";
import { colorFit, pickStickers, STICKER_LIBRARY } from "./sticker-library";

const chosen = (keywords: string[], palette: string[] = []) => pickStickers(keywords, palette).filter((p) => p.chosen).map((p) => p.sticker.id);

describe("sticker picker", () => {
  it("keeps the rainy-day choice", () => {
    expect(chosen(["rain", "moody", "street", "walk", "film", "friend", "churros", "cafe"])).toEqual(["umbrella-yellow", "cloud-soft"]);
  });
  it("needs a content match for specific things", () => {
    expect(chosen(["brunch", "eggs"])).toContain("eggs-benedict-watercolor");
    // a warm yellow palette alone never pulls in eggs benedict or a bicycle
    const warm = ["#e1c071", "#ee9236", "#8c6d4d", "#b49771"];
    const byColour = chosen([], warm);
    expect(byColour).not.toContain("eggs-benedict-watercolor");
    expect(byColour).not.toContain("bicycle-vintage");
    expect(byColour.every((id) => STICKER_LIBRARY.find((s) => s.id === id)!.generic)).toBe(true);
  });
  it("lets generic decoration in on colour fit only when the colours really match", () => {
    const beige = ["#a08a66", "#c2ac7e", "#7c6a53"];
    expect(colorFit(STICKER_LIBRARY.find((s) => s.id === "pressed-wildflowers")!, beige)).toBeGreaterThan(0.8);
    expect(chosen([], beige)).toContain("pressed-wildflowers");
    expect(chosen([], ["#1d3b8a", "#0b1a40"])).toEqual([]); // nothing fits deep navy
  });
  it("allows at most one photographic sticker and one per kind", () => {
    const picks = pickStickers(["picnic", "fruit", "cherries", "tree", "park", "summer"], [], 4).filter((p) => p.chosen).map((p) => p.sticker);
    expect(picks.filter((s) => s.medium.includes("photo")).length).toBeLessThanOrEqual(1);
    expect(new Set(picks.map((s) => s.kind)).size).toBe(picks.length);
  });
});
