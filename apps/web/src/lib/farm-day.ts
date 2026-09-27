/**
 * Prepared farm-day demo memory.
 *
 * This is intentionally a hand-authored fixture, not output from the live
 * weaving pipeline. Its fixed 1600 x 1000 plan lets the demo jump straight
 * from the Calendar to a finished spread while every item retains source_ids.
 */

export const FARM_CANVAS = { width: 1600, height: 1000 };

export type FarmTreatment = "PRESERVE" | "DISTILL" | "AUTHOR";
export type FarmProvenance = {
  label: string;
  treatment: FarmTreatment;
  detail: string;
  source_ids: string[];
};

type FarmBox = { x: number; y: number; w: number; h: number; r?: number; z?: number };
export type FarmElement = FarmBox & {
  kind: "photo" | "art";
  id: string;
  src: string;
  alt: string;
  frame: "photo" | "print" | "cut";
  fit?: "cover" | "contain";
  time?: string;
  tape?: "rose" | "sage" | "ochre";
  tapeAt?: "top" | "corner";
  provenance: FarmProvenance;
};

export const FARM_STORY = {
  weekday: "Sunday",
  date: "September 6",
  year: "2026",
  subtitle: "a day among the little animals",
  keywords: ["farm", "puppies", "Leila", "matcha"],
  palette: { name: "Farm Afternoon", swatches: ["#f4eee0", "#8da18b", "#d88996", "#c99b52", "#594234"] },
};

const P = "/memories/farm-day";

export const FARM_ELEMENTS: FarmElement[] = [
  {
    kind: "photo", id: "puppies-original", src: `${P}/puppies-original.jpg`,
    alt: "Leila sitting happily in the middle of a group of puppies", time: "12:05 pm",
    frame: "photo", fit: "cover", tape: "sage", tapeAt: "top",
    x: 76, y: 315, w: 310, h: 440, r: -1.5, z: 4,
    provenance: { label: "Photo · IMG_0591", treatment: "PRESERVE", detail: "Your original, shown as taken · 12:05 pm", source_ids: ["IMG_0591.HEIC"] },
  },
  {
    kind: "photo", id: "farm-original", src: `${P}/farm-original.jpg`,
    alt: "A woman holding a tiny animal with alpacas beside her", time: "11:20 am",
    frame: "photo", fit: "cover", tape: "rose", tapeAt: "corner",
    x: 414, y: 315, w: 310, h: 440, r: 1.5, z: 4,
    provenance: { label: "Photo · IMG_3558", treatment: "PRESERVE", detail: "Your original, shown as taken · 11:20 am", source_ids: ["IMG_3558.JPG"] },
  },
  {
    kind: "art", id: "basket-bunny", src: `${P}/basket-bunny.png`,
    alt: "A bunny in a basket rendered as a cropped tape collage", frame: "cut", fit: "contain",
    x: 510, y: 80, w: 220, h: 215, r: 3.2, z: 4,
    provenance: { label: "Tape collage · basket bunny", treatment: "DISTILL", detail: "AI-processed tape study, cropped from its paper field", source_ids: ["codex-clipboard-b2b9f2a6"] },
  },
  {
    kind: "art", id: "gathered-puppies", src: `${P}/gathered-puppies.png`,
    alt: "A full gathered-scenes composition of a woman surrounded by corgis", frame: "print", fit: "contain",
    x: 844, y: 68, w: 330, h: 550, r: -1.1, z: 3,
    provenance: { label: "Gathered scenes · puppies", treatment: "DISTILL", detail: "Full generated composition, shown uncropped", source_ids: ["codex-clipboard-baa8ded4"] },
  },
  {
    kind: "photo", id: "matcha-original", src: `${P}/matcha-original.jpg`,
    alt: "Matcha lattes and small cakes at a cafe", time: "3:40 pm",
    frame: "photo", fit: "cover", tape: "ochre", tapeAt: "top",
    x: 1220, y: 105, w: 270, h: 360, r: 2.4, z: 4,
    provenance: { label: "Photo · IMG_0618", treatment: "PRESERVE", detail: "Your original, shown as taken · 3:40 pm", source_ids: ["IMG_0618.heic"] },
  },
  {
    kind: "art", id: "bench-goat", src: `${P}/bench-goat.png`,
    alt: "A goat on a wooden bench rendered as a cropped tape collage", frame: "cut", fit: "contain",
    x: 990, y: 752, w: 226, h: 210, r: -4.2, z: 5,
    provenance: { label: "Tape collage · bench goat", treatment: "DISTILL", detail: "AI-processed tape study, cropped around the goat and bench", source_ids: ["codex-clipboard-b0286bfb"] },
  },
  {
    kind: "art", id: "alpaca-doodle", src: `${P}/alpaca-doodle.png`,
    alt: "A cropped colorful doodle of alpacas looking out from their enclosure", frame: "cut", fit: "contain",
    x: 1212, y: 566, w: 306, h: 392, r: 2.1, z: 4,
    provenance: { label: "Doodle · alpacas", treatment: "DISTILL", detail: "AI-processed drawing, cropped from its paper field", source_ids: ["codex-clipboard-c25036dc"] },
  },
];

export const FARM_TEXT = [
  { id: "farm-note", text: "We went to the farm that day and saw so many cute little animals.", x: 430, y: 800, w: 305 },
  { id: "puppy-note", text: "Leila and I were so happy to be surrounded by puppies.", x: 862, y: 654, w: 300 },
  { id: "matcha-note", text: "Matcha lattes afterwards were amazing.", x: 1224, y: 488, w: 276 },
];
