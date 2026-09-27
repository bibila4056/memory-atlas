/**
 * Memory index for the Calendar (DESIGN.md §10). Each entry's Memory Stamp is derived from the
 * spread's own elements, so a day is decorated only with things that were really on its pages:
 *   1. hero  — the skill-processed cut-out (tape collage / gathered scenes): unique to that day, shown largest
 *   2. stickers — library stickers used that day, small accents
 *   3. palette — for a faint wash behind the date
 */
import { ELEMENTS, STORY } from "./rainy-day";
import { FARM_ELEMENTS, FARM_STORY } from "./farm-day";

export type MemoryEntry = {
  date: string;           // YYYY-MM-DD
  slug: string;
  title: string;
  subtitle: string;
  keywords: string[];
  hero: { src: string; label: string } | null;
  stickers: { src: string; label: string }[];
  photos: string[];
  palette: string[];
};

const rainyDay: MemoryEntry = {
  date: "2026-09-12",
  slug: "rainy-day",
  title: `${STORY.weekday}, ${STORY.date}`,
  subtitle: STORY.subtitle,
  keywords: STORY.keywords,
  // Skill-processed art that was cut out by hand takes priority over framed art (e.g. the zine print).
  hero: (() => {
    const art = ELEMENTS.filter((el) => el.kind === "art");
    const pick = art.find((el) => el.kind === "art" && el.frame === "cut") ?? art[0];
    return pick ? { src: pick.src, label: pick.provenance.label } : null;
  })(),
  stickers: ELEMENTS.filter((el) => el.kind === "sticker").map((el) => ({ src: el.src, label: el.provenance.label.replace("Sticker · ", "") })),
  photos: ELEMENTS.filter((el) => el.kind === "photo").map((el) => el.src),
  palette: STORY.palette.swatches,
};

const farmDay: MemoryEntry = {
  date: "2026-09-06",
  slug: "farm-day",
  title: `${FARM_STORY.weekday}, ${FARM_STORY.date}`,
  subtitle: FARM_STORY.subtitle,
  keywords: FARM_STORY.keywords,
  hero: (() => {
    const pick = FARM_ELEMENTS.find((el) => el.id === "basket-bunny");
    return pick ? { src: pick.src, label: pick.provenance.label } : null;
  })(),
  stickers: FARM_ELEMENTS.filter((el) => ["bench-goat", "alpaca-doodle"].includes(el.id))
    .map((el) => ({ src: el.src, label: el.provenance.label })),
  photos: FARM_ELEMENTS.filter((el) => el.kind === "photo").map((el) => el.src),
  palette: FARM_STORY.palette.swatches,
};

export const MEMORIES: MemoryEntry[] = [rainyDay, farmDay];

export const SESSIONS_KEY = "memory-atlas.memory-sessions";

/** Which capture session produced a given day's memory (set when weaving finishes), so reopening keeps its words and voice. */
export function sessionFor(date: string): string | null {
  try { return JSON.parse(localStorage.getItem(SESSIONS_KEY) ?? "{}")[date] ?? null; } catch { return null; }
}

export function rememberSession(date: string, sessionId: string) {
  try {
    const all = JSON.parse(localStorage.getItem(SESSIONS_KEY) ?? "{}");
    localStorage.setItem(SESSIONS_KEY, JSON.stringify({ ...all, [date]: sessionId }));
  } catch { /* private mode: the calendar still opens the memory, just without this session's words */ }
}

export function memoryHref(entry: MemoryEntry, session: string | null) {
  return `/memories/${entry.slug}${session ? `?session=${session}` : ""}`;
}
