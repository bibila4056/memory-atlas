/**
 * Sticker library: generic ephemera, never evidence (no source_ids).
 * Data lives in public/stickers/library.json, built from stickers/catalog.json by scripts/build_stickers.py.
 *
 * A sticker may join a spread only when it belongs there (docs/ART_DIRECTION.md §E):
 *  • content match: its tags/moods overlap the story's own words, or
 *  • colour fit: it is `generic` decoration AND its palette sits close to the spread's palette.
 * Specific things (eggs benedict, a bicycle) always need a content match, so nothing feels random.
 * At most one photographic sticker, one per kind, MAX_STICKERS per spread.
 */
import library from "../../public/stickers/library.json";

export type Sticker = {
  id: string; src: string; label: string; kind: string; medium: string; generic: boolean;
  role: "accent" | "corner" | "hero"; tags: string[]; moods: string[]; aspect: number;
  palette: { hex: string; share: number }[]; notes: string;
};
export type StickerPick = { sticker: Sticker; score: number; chosen: boolean; reason: string };

export const MAX_STICKERS = 2;
export const STICKER_LIBRARY = library.stickers as Sticker[];
const COLOR_FIT_MIN = 0.62;

function lab(hex: string): [number, number, number] {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((v) => (v > 0.04045 ? ((v + 0.055) / 1.055) ** 2.4 : v / 12.92));
  const [x, y, z] = [
    (c[0] * 0.4124 + c[1] * 0.3576 + c[2] * 0.1805) / 0.95047,
    c[0] * 0.2126 + c[1] * 0.7152 + c[2] * 0.0722,
    (c[0] * 0.0193 + c[1] * 0.1192 + c[2] * 0.9505) / 1.08883,
  ].map((t) => (t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116));
  return [116 * y - 16, 500 * (x - y), 200 * (y - z)];
}

/** 1 = the sticker's colours already live in the spread, 0 = they would clash. Share-weighted nearest ΔE. */
export function colorFit(sticker: Sticker, spread: string[]): number {
  if (!spread.length) return 0;
  const targets = spread.map(lab);
  const d = sticker.palette.reduce((sum, p) => {
    const [l, a, b] = lab(p.hex);
    return sum + p.share * Math.min(...targets.map(([L, A, B]) => Math.hypot(l - L, a - A, b - B)));
  }, 0);
  return Math.max(0, 1 - d / 60);
}

const words = (list: string[]) => new Set(list.flatMap((w) => w.toLowerCase().split(/[^a-z]+/)).filter(Boolean));

export function pickStickers(keywords: string[], palette: string[] = [], max = MAX_STICKERS): StickerPick[] {
  const story = words(keywords);
  const scored = STICKER_LIBRARY.map((sticker) => {
    // Mirrors apps/api/app/stickers.py (the backend pick is canonical; this is the offline fallback).
    const tagHits = sticker.tags.filter((t) => story.has(t));
    const moodHits = sticker.generic ? sticker.moods.filter((t) => story.has(t) && !tagHits.includes(t)) : [];
    const hits = [...tagHits, ...moodHits], fit = colorFit(sticker, palette);
    const eligible = hits.length > 0 || (sticker.generic && fit >= COLOR_FIT_MIN);
    return { sticker, hits, fit, eligible, content: tagHits.length > 0, score: tagHits.length + 0.5 * moodHits.length + fit * 0.8 };
  }).sort((a, b) => Number(b.eligible) - Number(a.eligible) || Number(b.content) - Number(a.content) || b.score - a.score || a.sticker.id.localeCompare(b.sticker.id));
  const kinds = new Set<string>();
  let photographic = 0, taken = 0;
  return scored.map(({ sticker, hits, fit, eligible, score }) => {
    const photo = sticker.medium.includes("photo");
    const blocked = !eligible ? "not part of this story" : kinds.has(sticker.kind) ? "already have one like it"
      : photo && photographic ? "too close to the real photos" : taken >= max ? "one is enough" : null;
    if (!blocked) { taken++; kinds.add(sticker.kind); if (photo) photographic++; }
    const reason = blocked ?? (hits.length ? `echoes “${hits.slice(0, 3).join(", ")}”` : `colours already on the page (${Math.round(fit * 100)}%)`);
    return { sticker, score: Math.round(score * 100) / 100, chosen: !blocked, reason };
  });
}
