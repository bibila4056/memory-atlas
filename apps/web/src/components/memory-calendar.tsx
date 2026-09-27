"use client";

import Link from "next/link";
import { useMemo, useState, useSyncExternalStore } from "react";
import { MEMORIES, memoryHref, sessionFor, type MemoryEntry } from "@/lib/memories";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const iso = (y: number, m: number, d: number) => `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
const noop = () => () => {};

/** Gentle, repeatable scatter so each stamp looks hand-placed but never moves between visits. */
function jitter(seed: string, n: number) {
  let h = 0;
  for (const c of seed) h = (h * 31 + c.charCodeAt(0)) | 0;
  return ((Math.abs(h) % 1000) / 1000) * n - n / 2;
}

function Stamp({ entry }: { entry: MemoryEntry }) {
  return <span className="stamp" aria-hidden="true" style={{ "--wash": entry.palette[2] ?? "#b8543f" } as React.CSSProperties}>
    {entry.hero && /* eslint-disable-next-line @next/next/no-img-element */
      <img className="stamp-hero" src={entry.hero.src} alt="" style={{ rotate: `${jitter(entry.date, 14)}deg` }} />}
    {entry.stickers.slice(0, 2).map((s, i) => /* eslint-disable-next-line @next/next/no-img-element */
      <img key={s.src} className={`stamp-sticker stamp-sticker--${i}`} src={s.src} alt="" style={{ rotate: `${jitter(entry.date + s.src, 30)}deg` }} />)}
  </span>;
}

export function MemoryCalendar() {
  const byDate = useMemo(() => new Map(MEMORIES.map((m) => [m.date, m])), []);
  const latest = [...MEMORIES].sort((a, b) => b.date.localeCompare(a.date))[0];
  const todayIso = useSyncExternalStore(noop, () => { const t = new Date(); return iso(t.getFullYear(), t.getMonth(), t.getDate()); }, () => "");
  const start = latest ? new Date(`${latest.date}T12:00:00`) : new Date();
  const [month, setMonth] = useState({ y: start.getFullYear(), m: start.getMonth() });
  const [picked, setPicked] = useState<string | null>(latest?.date ?? null);
  const [hovered, setHovered] = useState<string | null>(null);
  const sessions = useSyncExternalStore(noop, () => JSON.stringify(Object.fromEntries(MEMORIES.map((m) => [m.date, sessionFor(m.date)]))), () => "{}");
  const sessionOf = (date: string): string | null => JSON.parse(sessions)[date] ?? null;

  const first = new Date(month.y, month.m, 1);
  const days = new Date(month.y, month.m + 1, 0).getDate();
  const cells = [...Array(first.getDay()).fill(null), ...Array.from({ length: days }, (_, i) => i + 1)];
  while (cells.length % 7) cells.push(null);
  const monthName = first.toLocaleDateString("en-US", { month: "long" });
  const shift = (delta: number) => setMonth(({ y, m }) => { const d = new Date(y, m + delta, 1); return { y: d.getFullYear(), m: d.getMonth() }; });
  const inMonth = MEMORIES.filter((m) => m.date.startsWith(iso(month.y, month.m, 1).slice(0, 7))).length;
  const shown = byDate.get(hovered ?? picked ?? "") ?? null;

  return <div className="notebook-boards"><section className="capture-notebook calendar-notebook" aria-label="Memory calendar">
    <div className="capture-page-left calendar-left">
      <header className="calendar-head">
        <h1><em>{monthName}</em> {month.y}</h1>
        <div className="calendar-nav">
          <button type="button" onClick={() => shift(-1)} aria-label="Previous month">‹</button>
          <button type="button" onClick={() => shift(1)} aria-label="Next month">›</button>
        </div>
      </header>
      <p className="calendar-count">{inMonth ? `${inMonth} ${inMonth === 1 ? "memory" : "memories"} this month` : "No memories this month yet"}</p>
      <div className="calendar-grid" role="grid" aria-label={`${monthName} ${month.y}`}>
        {WEEKDAYS.map((d) => <span key={d} className="calendar-weekday" role="columnheader">{d}</span>)}
        {cells.map((day, i) => {
          if (!day) return <span key={`blank-${i}`} className="calendar-day calendar-day--blank" aria-hidden="true" />;
          const date = iso(month.y, month.m, day);
          const entry = byDate.get(date);
          const common = { "data-today": date === todayIso || undefined, "data-picked": entry && picked === date || undefined };
          if (!entry) return <span key={date} className="calendar-day" role="gridcell" {...common}><span className="calendar-num">{day}</span></span>;
          return <Link key={date} href={memoryHref(entry, sessionOf(date))} role="gridcell" className="calendar-day calendar-day--memory" {...common}
            aria-label={`${entry.title}: ${entry.subtitle}. Open this memory`}
            onMouseEnter={() => setHovered(date)} onMouseLeave={() => setHovered(null)} onFocus={() => { setHovered(date); setPicked(date); }} onBlur={() => setHovered(null)}>
            <span className="calendar-num">{day}</span>
            <Stamp entry={entry} />
          </Link>;
        })}
      </div>
    </div>

    <div className="capture-page-right calendar-right">
      {shown ? <article className="calendar-preview" key={shown.date}>
        <p className="calendar-preview-date">{shown.title}</p>
        <h2>{shown.subtitle}</h2>
        <p className="calendar-preview-keywords">{shown.keywords.join(" / ")}</p>
        <div className="calendar-preview-collage">
          {shown.photos.slice(0, 3).map((src, i) => /* eslint-disable-next-line @next/next/no-img-element */
            <img key={src} className={`preview-photo preview-photo--${i}`} src={src} alt="" />)}
          {shown.hero && /* eslint-disable-next-line @next/next/no-img-element */
            <img className="preview-hero" src={shown.hero.src} alt={shown.hero.label} />}
          {shown.stickers.slice(0, 2).map((s, i) => /* eslint-disable-next-line @next/next/no-img-element */
            <img key={s.src} className={`preview-sticker preview-sticker--${i}`} src={s.src} alt="" />)}
        </div>
        <Link className="weave-button calendar-open" href={memoryHref(shown, sessionOf(shown.date))}>Open this memory
          <svg width="22" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" aria-hidden="true"><path d="M4 12h16m-6-6 6 6-6 6" /></svg></Link>
      </article> : <div className="empty-fragments"><div className="empty-paper-stack" aria-hidden="true"><div /><div /></div><p>Nothing woven this month.</p>
        <span><Link href="/">Capture a day</Link> and it will appear here.</span></div>}
    </div>
  </section></div>;
}
