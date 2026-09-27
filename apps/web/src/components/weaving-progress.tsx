"use client";

/**
 * Weaving screen. Every line and picture comes from the real pipeline:
 *   gather     ← the session (fragments + the author's choices)
 *   listen     ← /api/clarify: voice notes transcribed (shown, or understood quietly), notes read
 *   understand ← /api/clarify: what each photo shows; the one question it can't answer (conversation)
 *   story      ← /api/weave: moments, roles, title (BundleWeaver-lite)
 *   art        ← /api/weave: palette, art tool per photo, sticker drawer with scores and reasons
 *   compose    ← /api/weave: art requests, then the spread
 * Progress is proportional: each stage has a share of the run and completes only when its work is done;
 * while waiting it keeps creeping (never frozen, never jumping back), and it pauses while a question is open.
 */
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import type { CaptureSession } from "@/lib/capture";
import type { components } from "@/lib/api-schema";
import { MEMORIES, rememberSession } from "@/lib/memories";
import { STICKERS, STORY } from "@/lib/rainy-day";
import type { WeaveResult } from "@/lib/weave";

type Understanding = components["schemas"]["ClarifyResult"];
type Question = Understanding["questions"][number];
type StageKey = "gather" | "listen" | "understand" | "story" | "art" | "compose";
const STAGES: { key: StageKey; title: string; weight: number }[] = [
  { key: "gather", title: "Gathering your fragments", weight: 1 },
  { key: "listen", title: "Listening and reading", weight: 1.3 },
  { key: "understand", title: "Looking closely", weight: 1.4 },
  { key: "story", title: "Finding the story", weight: 1.4 },
  { key: "art", title: "Choosing art and stickers", weight: 1.6 },
  { key: "compose", title: "Cutting and composing", weight: 1.3 },
];
const TOTAL = STAGES.reduce((sum, s) => sum + s.weight, 0);
const TOOL_NAME = { tape_collage: "tape collage", doodle: "doodle", scene_extension: "gathered scenes" } as const;

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;
const clock = (iso?: string | null) => (iso ? new Date(iso).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }).toLowerCase() : "");
function guessMatch(reply: string, guess?: string) { return !!guess && reply === `This is ${guess}.`; }

export function WeavingProgress({ sessionId, seconds }: { sessionId?: string; seconds: number }) {
  const [session, setSession] = useState<CaptureSession | null>(null);
  const [seen, setSeen] = useState<Understanding | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [weave, setWeave] = useState<WeaveResult | null>(null);
  const [weaveSettled, setWeaveSettled] = useState(!sessionId);
  const [view, setView] = useState({ stage: 0, fraction: 0, done: false });

  // ── data ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!sessionId) return;
    fetch(`/api/session/${sessionId}`).then((r) => (r.ok ? r.json() : null)).then(setSession).catch(() => {});
    fetch("/api/clarify", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: sessionId }) })
      .then((r) => (r.ok ? r.json() : null)).then((r: Understanding | null) => { setSeen(r ?? { questions: [], photos: [], voices: [] }); setQuestions(r?.questions ?? []); })
      .catch(() => setSeen({ questions: [], photos: [], voices: [] }));
  }, [sessionId]);
  const understood = !sessionId || (seen !== null && questions.length === 0);
  useEffect(() => {  // the story is woven only after the author has answered (or skipped)
    if (!sessionId || !understood) return;
    fetch("/api/weave", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: sessionId }) })
      .then((r) => (r.ok ? r.json() : null)).then(setWeave).catch(() => null).finally(() => setWeaveSettled(true));
  }, [sessionId, understood]);

  // ── progress engine ─────────────────────────────────────────────────
  const ready = useRef<Record<StageKey, boolean>>({ gather: false, listen: false, understand: false, story: false, art: false, compose: false });
  const asking = useRef(false);
  const stageNow = STAGES[Math.min(view.stage, STAGES.length - 1)].key;
  const showQuestion = !view.done && stageNow === "understand" && questions.length > 0 && view.fraction >= 0.35;
  useEffect(() => {
    ready.current = { gather: !sessionId || session !== null, listen: !sessionId || seen !== null, understand: understood,
      story: weaveSettled, art: weaveSettled, compose: weaveSettled };
    asking.current = showQuestion;
  }, [sessionId, session, seen, understood, weaveSettled, showQuestion]);
  useEffect(() => {
    let frame = 0, last: number | null = null, stage = 0, t = 0;
    const tick = (now: number) => {
      const dt = last === null ? 0 : Math.min(0.25, (now - last) / 1000);
      last = now;
      if (!asking.current) t += dt;
      const d = (seconds * STAGES[stage].weight) / TOTAL;
      const isReady = ready.current[STAGES[stage].key];
      // Ready: fill linearly to 100%. Not ready: fill to 85%, then keep creeping toward 99% (never frozen).
      const fraction = isReady || t < 0.85 * d ? Math.min(1, t / d) : 0.85 + 0.14 * (1 - Math.exp(-(t - 0.85 * d) / d));
      if (fraction >= 1 && isReady) {
        if (stage === STAGES.length - 1) { setView({ stage, fraction: 1, done: true }); return; }
        stage += 1; t = 0;
      }
      setView({ stage, fraction: fraction >= 1 ? 0 : fraction, done: false });
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [seconds]);
  const progress = view.done ? 1 : (STAGES.slice(0, view.stage).reduce((s, x) => s + x.weight, 0) + view.fraction * STAGES[view.stage].weight) / TOTAL;
  const remaining = view.done ? 0 : ((1 - view.fraction) * STAGES[view.stage].weight + STAGES.slice(view.stage + 1).reduce((s, x) => s + x.weight, 0)) / TOTAL * seconds;
  const leftLabel = view.done ? "Done" : showQuestion ? "paused for your answer" : remaining > 90 ? `about ${Math.round(remaining / 60)} minutes left` : remaining > 40 ? "about a minute left" : "almost there";
  useEffect(() => { if (view.done && sessionId && MEMORIES[0]) rememberSession(weave?.day ?? MEMORIES[0].date, sessionId); }, [view.done, sessionId, weave?.day]);

  async function answer(question: Question, reply: string | null, said: string) {
    setQuestions((qs) => qs.filter((q) => q.id !== question.id));
    const turns = [{ role: "weaver", text: question.text, source_id: question.source_id, question_id: question.id },
                   { role: "author", text: said, source_id: question.source_id, question_id: question.id }];
    const saved = await fetch(`/api/session/${sessionId}/conversation`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(turns) })
      .then((r) => (r.ok ? r.json() : null)).catch(() => null);
    if (saved) setSession(saved);
    if (!reply) return;  // skipped: the spread simply leaves that detail out
    const fragment = session?.fragments.find((f) => f.id === question.source_id);
    await fetch(`/api/source/${question.source_id}`, { method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keep_original: fragment?.keep_original ?? true, source_instruction: reply }) }).catch(() => null);
  }

  // ── what each stage says (all derived from real results) ────────────
  const fragments = session?.fragments ?? [];
  const photos = fragments.filter((f) => f.modality === "image");
  const notes = fragments.filter((f) => f.modality === "text");
  const voices = fragments.filter((f) => f.modality === "audio");
  const photoNo = (id: string) => photos.findIndex((p) => p.id === id) + 1;
  const media = (id: string) => `/api/source/${id}/media`;
  const artCount = photos.filter((p) => !p.keep_original).length;
  const heard = seen?.voices ?? [];
  const times = (seen?.photos ?? []).map((p) => p.captured_at).filter((t): t is string => !!t).sort();
  const mainDay = times.length ? times.map((t) => t.slice(0, 10)).sort((a, b) => times.filter((t) => t.startsWith(b)).length - times.filter((t) => t.startsWith(a)).length)[0] : null;
  const dayTimes = times.filter((t) => t.startsWith(mainDay ?? "~"));
  const byMoment = new Map(weave?.moments.map((m) => [m.id, m]) ?? []);
  const chosenStickers = weave ? weave.stickers : STICKERS.map((p) => ({ id: p.sticker.id, label: p.sticker.label, src: p.sticker.src, chosen: p.chosen, reason: p.reason, matched: [], color_fit: 0 }));
  const fits = chosenStickers.filter((s) => s.chosen);

  const lines: Record<StageKey, string[]> = {
    gather: session ? [
      [plural(photos.length, "photo"), notes.length && plural(notes.length, "note"), voices.length && plural(voices.length, "voice note")].filter(Boolean).join(", ") + ".",
      artCount ? `${photos.length - artCount} stay exactly as taken; ${artCount} may become art.` : `All ${plural(photos.length, "photo")} stay exactly as taken.`,
      "Reading when each photo was taken.",
    ] : ["Gathering your photos, words and voice."],
    listen: [
      ...heard.map((v, i) => v.status !== "transcribed" ? `Voice note ${i + 1} stays as sound (transcription isn’t connected).`
        : v.shown_as_text ? `Writing down voice note ${i + 1}, word for word.` : `Listening to voice note ${i + 1} quietly; it stays as your voice.`),
      notes.length ? (notes.some((n) => !n.keep_original) ? `Reading ${plural(notes.length, "note")}; tidying grammar only where you asked.` : `Reading ${plural(notes.length, "note")}, exactly as written.`) : "",
    ].filter(Boolean),
    understand: [
      ...(seen?.photos ?? []).map((p) => `Photo ${photoNo(p.source_id)}: ${p.labels.slice(0, 3).join(", ") || "looking…"}.`),
      dayTimes.length > 1 ? `Taken between ${clock(dayTimes[0])} and ${clock(dayTimes[dayTimes.length - 1])}.` : "",
    ].filter(Boolean),
    story: weave ? [
      `${plural(weave.moments.length, "moment")} in this day.`,
      ...weave.selected.moment_ids.map((id) => `${byMoment.get(id)?.title ?? id} → ${weave.selected.roles[id]?.toLowerCase()}.`),
      weave.duplicate_groups.length ? `Set aside ${plural(weave.duplicate_groups.reduce((n, g) => n + g.source_ids.length - 1, 0), "near-identical shot")}; every original is kept.` : "",
      `Calling it “${weave.story.title}”.`,
    ].filter(Boolean) : ["Grouping photos, words and voice into moments."],
    art: weave ? [
      "Palette taken from the photos that made it in.",
      ...(weave.art?.requests ?? []).map((r) => `Photo ${photoNo(r.source_id)} → ${TOOL_NAME[r.tool]}.`),
      `Opening the sticker drawer: ${plural(chosenStickers.length, "sticker")}, ${fits.length} fit this day.`,
    ] : ["Choosing colours, art and stickers."],
    compose: [
      ...(weave?.art?.requests ?? []).filter((r) => r.placement === "beside_original").map((r) => `Cutting out the ${TOOL_NAME[r.tool]} for photo ${photoNo(r.source_id)}.`),
      "Taping each print to the page, leaving room to breathe.",
      "Writing the date at the top.",
    ],
  };
  const stage = STAGES[view.stage];
  const stageLines = lines[stage.key].length ? lines[stage.key] : [stage.title + "…"];
  const line = stageLines[Math.min(stageLines.length - 1, Math.floor(view.fraction * stageLines.length))];
  const dayLabel = weave?.day ? new Date(`${weave.day}T12:00:00`).toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" }) : `${STORY.weekday}, ${STORY.date}`;
  const tapeFor = weave?.art?.requests.find((r) => r.tool === "tape_collage");
  const tapeSrc = tapeFor && fragments.find((f) => f.id === tapeFor.source_id)?.filename === "IMG_3456.jpeg" ? "/memories/rainy-day/churros-cutout.png" : tapeFor ? media(tapeFor.source_id) : "/memories/rainy-day/churros-cutout.png";
  const key = view.done ? "done" : stage.key;

  return <main className="capture-page weave-page">
    {/* eslint-disable-next-line @next/next/no-img-element */}
    <img className="desk-botanical desk-botanical--bottom" src="/illustrations/sprig-a.png" alt="" aria-hidden="true" />
    <header className="capture-masthead"><Link href="/" className="wordmark">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="wordmark-sprig" src="/illustrations/mark.png" alt="" aria-hidden="true" />
      Memory Atlas</Link></header>
    <div className="notebook-tabs"><span aria-current="page">Weaving</span></div>
    <div className="notebook-boards"><section className="capture-notebook" aria-label="Weaving your memory">
      <div className="capture-page-left weave-left">
        <h1>{view.done ? <>Your memory<br />is <em>ready</em>.</> : <>Weaving<br />your <em>memory</em></>}</h1>
        {!view.done && <p className="capture-intro">A good collage takes time.</p>}
        <div className="weave-progress" role="progressbar" aria-label="Weaving progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress * 100)}>
          <div className="weave-bar"><span style={{ width: `${progress * 100}%` }} /><i style={{ left: `${progress * 100}%` }} aria-hidden="true" /></div>
          <div className="weave-meta"><span>{Math.round(progress * 100)}%</span><span>{leftLabel}</span></div>
        </div>
        <p className="weave-line" aria-live="polite" key={showQuestion ? "ask" : view.done ? "done" : line}>{showQuestion ? "One question for you, on the right →" : view.done ? "Finished. Take a look." : line}</p>
        <ol className="weave-steps">
          {STAGES.map((s, i) => <li key={s.key} data-state={view.done || i < view.stage ? "done" : i === view.stage ? "active" : "todo"}>
            <span className="weave-mark" aria-hidden="true" />{s.title}
          </li>)}
        </ol>
        {!!session?.conversation?.length && <div className="weave-convo" aria-label="Your conversation with the notebook">
          {session.conversation.map((turn, i) => <p key={i} className={`thread-turn thread-turn--${turn.role}`}>{turn.text}</p>)}
        </div>}
        {view.done && <Link className="weave-button weave-open" href={`/memories/rainy-day${sessionId ? `?session=${sessionId}` : ""}`}>Open your memory <svg width="22" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" aria-hidden="true"><path d="M4 12h16m-6-6 6 6-6 6" /></svg></Link>}
      </div>

      <div className="capture-page-right weave-right" data-step={key}>
        <p className="fragments-count">{showQuestion ? "A quick question" : view.done ? dayLabel : stage.title}</p>
        {showQuestion && <QuestionCard key={questions[0].id} question={questions[0]} photoNumber={photoNo(questions[0].source_id)} onAnswer={(reply, said) => void answer(questions[0], reply, said)} />}

        {!showQuestion && key === "gather" && <div className="weave-scatter">{(photos.length ? photos.map((p) => media(p.id)) : BASE_THUMBS).slice(0, 6).map((src, i) =>
          <figure key={src} style={{ left: [4, 52, 18, 60, 30, 8][i % 6] + "%", top: [4, 10, 40, 46, 70, 76][i % 6] + "%", "--rot": `${[-7, 5, 3, -4, 6, -2][i % 6]}deg`, animationDelay: `${i * 0.4}s` } as React.CSSProperties}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={src} alt="" /></figure>)}</div>}

        {!showQuestion && key === "listen" && <div className="weave-reading">
          {voices.length > 0 && <div className="weave-listen" aria-hidden="true">{Array.from({ length: 28 }, (_, i) => <i key={i} style={{ animationDelay: `${(i % 7) * 0.12}s` }} />)}</div>}
          {[...heard.filter((v) => v.text).map((v) => ({ id: v.source_id, text: v.text!, tag: v.shown_as_text ? "your voice, written down" : "heard quietly · stays as your voice" })),
            ...notes.map((n) => ({ id: n.id, text: n.original_text ?? "", tag: n.keep_original ? "your note" : "your note · grammar only" }))].slice(0, 3).map((item) =>
            <div key={item.id} className="weave-heard"><p className="weave-quote">{item.text.split(" ").map((w, i) => <span key={i} style={{ animationDelay: `${i * 0.08}s` }}>{w} </span>)}</p><small>{item.tag}</small></div>)}
        </div>}

        {!showQuestion && key === "understand" && <div className="weave-seen">{(seen?.photos ?? []).map((p) => <figure key={p.source_id}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={media(p.source_id)} alt="" />
          <figcaption>{p.labels.slice(0, 3).map((l) => <span key={l}>{l}</span>)}{p.people.map((n) => <span key={n} className="is-person">{n}</span>)}</figcaption>
        </figure>)}</div>}

        {!showQuestion && key === "story" && <div className="weave-moments">
          {(weave ? [...weave.selected.moment_ids, ...weave.moments.map((m) => m.id).filter((id) => !weave.selected.moment_ids.includes(id))].map((id) => byMoment.get(id)!).filter((m) => m?.image_source_ids.length).slice(0, 5)
            : []).map((m, i) => <div key={m.id} className="weave-moment" data-out={!weave!.selected.roles[m.id] || undefined} style={{ animationDelay: `${i * 0.4}s` }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={media(m.image_source_ids[0])} alt="" />
            <div><b>{m.title}</b>{m.source_ids.length > 1 && <small>{plural(m.source_ids.length, "fragment")}</small>}{weave!.selected.roles[m.id] && <span className="weave-role">{weave!.selected.roles[m.id]}</span>}</div>
          </div>)}
        </div>}

        {!showQuestion && key === "art" && <div className="weave-art">
          <div className="weave-swatches">{(weave?.palette ?? STORY.palette.swatches).map((c) => <i key={c} style={{ background: c }} />)}<span>From your photos</span></div>
          {!!weave?.art?.requests.length && <div className="weave-tools">{weave.art.requests.map((r) => <div key={r.source_id}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={media(r.source_id)} alt="" /><p><b>{TOOL_NAME[r.tool]}</b><small>{r.reason}</small></p></div>)}</div>}
          <p className="weave-drawer-title">Sticker drawer <small>{plural(chosenStickers.length, "sticker")} · chosen by content, then colour</small></p>
          <div className="weave-drawer">{[...fits, ...chosenStickers.filter((s) => !s.chosen)].slice(0, 8).map((pick, i) => <figure key={pick.id} data-chosen={pick.chosen} style={{ animationDelay: `${i * 0.25}s` }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={pick.src} alt="" />
            <figcaption>{pick.label}<small>{pick.reason}</small></figcaption></figure>)}</div>
        </div>}

        {!showQuestion && key === "compose" && <div className="weave-compose">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="weave-cutting" src={tapeSrc} alt="" />
          <p className="weave-scissors">cutting along the edge…</p>
        </div>}

        {key === "done" && <div className="weave-done">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={tapeSrc} alt="" />
          <p>{dayLabel}<br /><em>{weave?.story.title ?? STORY.subtitle}</em></p>
        </div>}
      </div>
    </section></div>
  </main>;
}

const BASE_THUMBS = ["rain-walk", "film-shop", "churros-photo", "window"].map((n) => `/memories/rainy-day/${n}.jpg`);

/** One question at a time, answerable from the keyboard: Y / N / 1–9 / S or Esc to skip. */
function QuestionCard({ question, photoNumber, onAnswer: send }: { question: Question; photoNumber: number; onAnswer: (reply: string | null, said: string) => void }) {
  const onAnswer = useCallback((reply: string | null) => {
    const said = reply === null ? "Skipped" : /^This is (.+)\.$/.test(reply) ? (guessMatch(reply, question.suggestions[0]) ? `Yes, it’s ${question.suggestions[0]}.` : `It’s ${reply.replace(/^This is |\.$/g, "")}.`) : reply;
    send(reply, said);
  }, [send, question]);
  const who = question.id.startsWith("who-");
  const guess = question.suggestions[0];
  const [typing, setTyping] = useState(false);
  const [name, setName] = useState("");
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (typing || event.metaKey || event.ctrlKey) return;
      const k = event.key.toLowerCase();
      if (k === "escape" || k === "s") onAnswer(null);
      else if (who && guess && k === "y") onAnswer(`This is ${guess}.`);
      else if (who && k === "n") setTyping(true);
      else if (!who && /^[1-9]$/.test(k) && question.suggestions[+k - 1]) onAnswer(`The ${question.text.match(/the (.+?) you/)?.[1] ?? "thing"} is in ${question.suggestions[+k - 1]}.`);
      else return;
      event.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [typing, who, guess, question, onAnswer]);
  return <div className="weave-question" role="dialog" aria-label="A quick question">
    {/* eslint-disable-next-line @next/next/no-img-element */}
    <img src={`/api/source/${question.source_id}/media`} alt={`Photo ${photoNumber}`} />
    <p className="weave-question-text">{question.text}</p>
    {typing ? <form className="weave-question-name" onSubmit={(event) => { event.preventDefault(); onAnswer(name.trim() ? `This is ${name.trim()}.` : null); }}>
      <input autoFocus value={name} onChange={(event) => setName(event.target.value)} placeholder="Who is it? (Enter to save, empty to skip)" aria-label="Who is it?"
        onKeyDown={(event) => { if (event.key === "Escape") onAnswer(null); }} />
    </form> : <div className="weave-question-actions">
      {who && guess && <button type="button" onClick={() => onAnswer(`This is ${guess}.`)}>Yes, it’s {guess} <kbd>Y</kbd></button>}
      {who && <button type="button" onClick={() => setTyping(true)}>{guess ? "No, it’s someone else" : "Tell me who"} <kbd>N</kbd></button>}
      {!who && question.suggestions.map((option, i) => <button type="button" key={option} onClick={() => onAnswer(`The ${question.text.match(/the (.+?) you/)?.[1] ?? "thing"} is in ${option}.`)}>{option} <kbd>{i + 1}</kbd></button>)}
      <button type="button" className="text-link" onClick={() => onAnswer(null)}>Skip <kbd>S</kbd></button>
    </div>}
  </div>;
}
