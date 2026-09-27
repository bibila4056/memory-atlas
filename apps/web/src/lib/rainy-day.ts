/**
 * Rainy-day demo weave: the curated result the Weaving screen hands off to.
 *
 * This is a prepared fixture for the product demo (see artifacts/rainy-day-weave).
 * Composition is a fixed 1600 × 1000 layered plan, like every Memory Spread:
 * originals are PRESERVED (resized for display only), derived art keeps its
 * source photo in `sources`, and stickers come from the library picker.
 */
import { pickStickers, STICKER_LIBRARY } from "./sticker-library";

export const CANVAS = { width: 1600, height: 1000 };

export type Treatment = "PRESERVE" | "DISTILL" | "LIBRARY" | "AUTHOR";
export type Provenance = { label: string; treatment: Treatment; detail: string };

export const STORY = {
  weekday: "Saturday",
  date: "September 12",
  year: "2026",
  subtitle: "a moody, rainy day",
  keywords: ["rain", "moody", "film shop", "Shelly", "churros"],
  moments: [
    { id: "walk", title: "Walking in the rain", role: "Anchor" },
    { id: "film", title: "The hidden film shop", role: "Detail" },
    { id: "morcilla", title: "Churros at Morcilla", role: "Closing" },
  ],
  palette: { name: "Rain Archive", swatches: ["#f4eee0", "#6f8193", "#b8543f", "#d8b04a", "#3c4a3a"] },
};

/** The library decides; the plan only positions whatever was chosen. */
export const STICKERS = pickStickers(["rain", "moody", "street", "walk", "film", "friend", "churros"], ["#504138", "#756e61", "#9d9d8d", "#c1c4cb", "#b37e55"], 3);

/** Sticker slots on this spread; the picker's choices fill them (sky slot prefers weather stickers). */
const SLOTS = [
  { prefer: "weather", x: 520, y: 72, w: 200, r: -3, z: 2 },   // above the film shop, with pencil rain beneath
  { prefer: "object", x: 362, y: 262, w: 128, r: 16, z: 5 },   // tucked by the walk photo
  { prefer: "", x: 302, y: 808, w: 116, r: -14, z: 5 },       // bottom of the left page
];
/** Place chosen stickers into this spread's slots. `chosen` comes from the weave (canonical) or, offline, the local picker. */
export function placeStickers(chosen: { id: string; reason: string }[] = STICKERS.filter((p) => p.chosen).map((p) => ({ id: p.sticker.id, reason: p.reason }))): StickerEl[] {
  const reasons = new Map(chosen.map((c) => [c.id, c.reason]));
  const picks = chosen.map((c) => STICKER_LIBRARY.find((s) => s.id === c.id)).filter((s): s is NonNullable<typeof s> => !!s);
  const free = [...SLOTS], out: StickerEl[] = [];
  for (const s of [...picks].sort((a, b) => Number(SLOTS.some((x) => x.prefer === b.kind)) - Number(SLOTS.some((x) => x.prefer === a.kind)))) {
    const i = Math.max(0, free.findIndex((slot) => slot.prefer === s.kind));
    const slot = free.splice(i, 1)[0];
    if (!slot) break;
    const why = reasons.get(s.id) ?? "";
    out.push({ kind: "sticker", id: s.id, src: s.src, alt: "", x: slot.x, y: slot.y, w: slot.w, h: Math.round(slot.w / s.aspect), r: slot.r, z: slot.z,
      provenance: { label: `Sticker · ${s.label.toLowerCase()}`, treatment: "LIBRARY", detail: `From the sticker drawer · ${why}` } });
  }
  return out;
}

type Box = { x: number; y: number; w: number; h: number; r?: number; z?: number };
export type PhotoEl = Box & { kind: "photo"; id: string; src: string; alt: string; time: string; tape?: "rose" | "sage" | "ochre"; tapeAt?: "top" | "corner"; provenance: Provenance };
export type ArtEl = Box & { kind: "art"; id: string; src: string; alt: string; frame?: "print" | "cut"; provenance: Provenance };
export type StickerEl = Box & { kind: "sticker"; id: string; src: string; alt: string; provenance: Provenance };
export type SpreadEl = PhotoEl | ArtEl | StickerEl;

const P = "/memories/rainy-day";
export const ELEMENTS: SpreadEl[] = [
  // ── left page: the walk + the film shop
  { kind: "photo", id: "rain-walk", src: `${P}/rain-walk.jpg`, alt: "Shelly walking in the rain under an umbrella", time: "4:43 pm",
    x: 92, y: 330, w: 330, h: 440, r: -2.4, z: 3, tape: "sage", tapeAt: "top",
    provenance: { label: "Photo · IMG_3310", treatment: "PRESERVE", detail: "Your original, shown as taken · 4:43 pm" } },
  { kind: "photo", id: "film-shop", src: `${P}/film-shop.jpg`, alt: "Inside the hidden film shop", time: "4:36 pm",
    x: 474, y: 322, w: 250, h: 333, r: 2.8, z: 3, tape: "rose", tapeAt: "corner",
    provenance: { label: "Photo · IMG_3292", treatment: "PRESERVE", detail: "Your original, shown as taken · 4:36 pm" } },
  // ── right page: the window, the churros, and the churros again in tape
  { kind: "art", id: "window-zine", src: `${P}/window-gathered.jpg`, alt: "The rainy window, continued as an illustrated zine page", frame: "print",
    x: 866, y: 92, w: 330, h: 550, r: -1.2, z: 2,
    provenance: { label: "Gathered scenes", treatment: "DISTILL", detail: "Drawn from your window photo · the photo stays intact inside it" } },
  { kind: "photo", id: "churros-photo", src: `${P}/churros-photo.jpg`, alt: "Churros, flan and a candle at Morcilla", time: "6:30 pm",
    x: 1272, y: 156, w: 250, h: 333, r: 3.2, z: 3, tape: "ochre", tapeAt: "top",
    provenance: { label: "Photo · IMG_3456", treatment: "PRESERVE", detail: "Your original, shown as taken · 6:30 pm" } },
  { kind: "art", id: "churros-tape", src: `${P}/churros-cutout.png`, alt: "The churros rebuilt from torn washi tape, cut out by hand", frame: "cut",
    x: 1200, y: 540, w: 330, h: 332, r: -5, z: 4,
    provenance: { label: "Tape collage", treatment: "DISTILL", detail: "Rebuilt from your churros photo in washi tape, then hand-cut" } },
];
/** The spread's own elements (photos + skill art); stickers are added from the weave's pick. */
export const BASE_ELEMENTS: SpreadEl[] = [...ELEMENTS];
ELEMENTS.push(...placeStickers());

/** Hand-drawn notes that point at things inside the photos (canvas coordinates). */
export const ANNOTATIONS = [
  { id: "shelly", text: "Shelly", x: 118, y: 842, path: "M170 846 C 196 790, 222 680, 246 590", head: { x: 246, y: 590, angle: -75 }, target: "rain-walk" },
  { id: "flan", text: "Spanish flan & churros", x: 1236, y: 62, path: "M1452 108 C 1462 190, 1446 300, 1424 386", head: { x: 1424, y: 386, angle: 101 }, target: "churros-photo" },
];

export const AUTHOR_NOTE_ORIGINAL = "It was a moody, rainy day. I went to this cute, hidden film shop with Shelly. The pouring rain kinda threw us off, but luckily the churros at Morcilla cheered us up.";
