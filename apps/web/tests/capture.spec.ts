import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import type { CaptureSession } from "../src/lib/capture";

test.use({ viewport: { width: 1440, height: 1000 }, permissions: ["microphone"], launchOptions: { args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"] } });

test("diary → multimodal capture → reload → weaving preserves original evidence", async ({ page, request }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await page.getByRole("button", { name: "Open your diary" }).click();
  await expect(page.getByRole("heading", { name: "What do you want to remember today?" })).toBeVisible();
  const started = Date.now();
  // Photos / Voice / Text come first; the writing space opens only when Text is chosen.
  await expect(page.getByRole("textbox", { name: "Your words", exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Text", exact: true }).click();
  const composer = page.getByRole("textbox", { name: "Your words", exact: true });
  await expect(composer).toBeEnabled();
  await composer.fill("on a rainy day\n  These are my exact words.  ");
  await page.getByLabel("Choose photos").setInputFiles(Array(8).fill("public/demo/flower-market-morning.png"));
  await expect(page.locator('[data-source-id]')).toHaveCount(8);
  // This uploads synthetic test audio; no invented recording enters the author's demo.
  const wav = Buffer.alloc(844); wav.write("RIFF", 0); wav.writeUInt32LE(836, 4); wav.write("WAVEfmt ", 8); wav.writeUInt32LE(16, 16); wav.writeUInt16LE(1, 20); wav.writeUInt16LE(1, 22); wav.writeUInt32LE(8000, 24); wav.writeUInt32LE(16000, 28); wav.writeUInt16LE(2, 32); wav.writeUInt16LE(16, 34); wav.write("data", 36); wav.writeUInt32LE(800, 40);
  await page.getByLabel("Choose voice recording").setInputFiles({ name: "test-voice.wav", mimeType: "audio/wav", buffer: wav });
  await expect(page.locator('[data-source-id]')).toHaveCount(9);
  await page.getByRole("button", { name: "Weave this memory" }).click();
  await expect(page).toHaveURL(/\/weave\?session=/);
  // The transcript checkpoint still lives at /weaving; the timed Weaving screen hands off to the spread.
  await page.goto(page.url().replace("/weave?", "/weaving?"));
  expect(Date.now() - started).toBeLessThan(30000);
  await expect(page.getByRole("heading", { name: "Ready to weave." })).toBeVisible();
  const id = new URL(page.url()).searchParams.get("session")!;
  const saved: CaptureSession = await (await request.get(`/api/session/${id}`)).json();
  expect(saved.fragments).toHaveLength(10);
  expect(saved.fragments.every((fragment) => fragment.keep_original)).toBe(true);
  expect(saved.allow_text_refinement).toBe(false);
  const photo = saved.fragments.find((fragment) => fragment.modality === "image")!;
  expect(await (await request.get(photo.original_media_ref!)).body()).toEqual(await readFile("public/demo/flower-market-morning.png"));
  const audio = saved.fragments.find((fragment) => fragment.modality === "audio")!;
  expect(await (await request.get(audio.original_media_ref!)).body()).toEqual(wav);
  // Once woven, the session is finished: plain Capture starts a brand-new page …
  expect((await request.post("/api/weave", { data: { session_id: id } })).ok()).toBe(true);  // what the weaving screen does
  expect((await (await request.get(`/api/session/${id}`)).json()).woven).toBe(true);
  await page.goto("/");
  await expect(page.getByText("Nothing collected yet")).toBeVisible();
  await expect(page.locator('[data-source-id]')).toHaveCount(0);
  // … while an explicit link still reopens the woven session on purpose.
  await page.goto(`/?session=${id}`);
  await expect(page.getByRole("button", { name: "Open your diary" })).toHaveCount(0);
  await expect(page.locator('[data-source-id]')).toHaveCount(10);
  const photoCard = page.locator(`[data-source-id="${photo.id}"]`);
  await photoCard.getByText('Make it art').click();
  await expect(photoCard.getByRole('radio', { name: 'Make it art' })).toBeChecked();
  // No page-wide busy state: the other controls never disable (this caused the flicker).
  await expect(page.getByRole("button", { name: "Photos", exact: true })).toBeEnabled();
  await photoCard.getByRole('button', { name: /Inspect/ }).click();
  const original = page.getByRole('dialog', { name: 'Original photo' }).locator('img');
  await expect(original).toBeVisible();
  const inspectorViewport = page.locator('.original-photo-scroll');
  const [photoBounds, viewportBounds] = await Promise.all([original.boundingBox(), inspectorViewport.boundingBox()]);
  expect(photoBounds).not.toBeNull();
  expect(viewportBounds).not.toBeNull();
  expect(photoBounds!.width).toBeLessThanOrEqual(viewportBounds!.width);
  expect(photoBounds!.height).toBeLessThanOrEqual(viewportBounds!.height);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.reload();
  await expect(page.locator('[data-source-id]')).toHaveCount(10);
  for (const fragment of saved.fragments) await expect(page.locator(`[data-source-id="${fragment.id}"]`)).toBeVisible();
  const restored: CaptureSession = await (await request.get(`/api/session/${id}`)).json();
  const note = restored.fragments.find((fragment) => fragment.modality === "text")!;
  expect(note.original_text).toBe("on a rainy day\n  These are my exact words.  ");
  expect(note.source_instruction).toBeNull();
  expect(restored.fragments.find((fragment) => fragment.id === photo.id)!.keep_original).toBe(false);
  // Any number of voice clips: a second one sits beside the first.
  await page.getByLabel("Choose voice recording").setInputFiles({ name: "second.wav", mimeType: "audio/wav", buffer: wav });
  await expect(page.locator(".captured-fragment--audio")).toHaveCount(2);
  await page.getByRole("button", { name: "Delete test-voice.wav", exact: true }).click();
  await expect(page.locator(".captured-fragment--audio")).toHaveCount(1);
  // Notes are editable in place.
  await page.locator(".captured-fragment--text .captured-note").click();
  await page.getByRole("textbox", { name: "Edit your words" }).fill("on a rainy day, revised");
  await page.getByRole("textbox", { name: "Edit your words" }).press("Meta+Enter");
  await expect(page.locator(".captured-fragment--text .captured-note")).toHaveText("on a rainy day, revised");
  expect(errors).toEqual([]);
});

test("reduced-motion opening skips the physical sequence; microphone records and saves", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await page.getByRole("button", { name: "Open your diary" }).click();
  await expect(page.locator('[data-phase="opening"]')).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Text", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "Voice", exact: true }).click();
  await page.getByRole("button", { name: "Start recording", exact: true }).click();
  await expect(page.getByText("Recording… Take your time.")).toBeVisible();
  // Let the fake microphone produce a short, non-empty real MediaRecorder clip.
  await page.waitForTimeout(400);
  await page.getByRole("button", { name: "Stop & save" }).click();
  await expect(page.locator("audio")).toHaveCount(1);
  await expect(page.getByRole("button", { name: "Voice", exact: true })).toBeEnabled();
  await page.reload();
  await expect(page.locator("audio")).toHaveCount(1);
});

test("the turning book lands on the already-mounted Capture paper", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator('.capture-notebook')).toHaveCount(1);
  await page.getByRole("button", { name: "Open your diary" }).click();
  await page.waitForTimeout(1100);
  const paper = await page.locator('.capture-notebook').boundingBox();
  const turning = await page.locator('.diary-stage').boundingBox();
  expect(paper).not.toBeNull(); expect(turning).not.toBeNull();
  expect(Math.abs(paper!.width - turning!.width)).toBeLessThan(3);
  expect(Math.abs(paper!.y - turning!.y)).toBeLessThan(3);
  await expect(page.locator('.diary-entrance')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Text', exact: true })).toBeEnabled();
});
