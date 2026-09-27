import { test, expect } from "@playwright/test";

test("voice excerpt plays only its original scheduled range; failures can retry", async ({ page, request }) => {
  const session = await (await request.post('/api/session', { data: {} })).json();
  const wav = Buffer.alloc(32044); wav.write('RIFF', 0); wav.writeUInt32LE(32036, 4); wav.write('WAVEfmt ', 8); wav.writeUInt32LE(16, 16); wav.writeUInt16LE(1, 20); wav.writeUInt16LE(1, 22); wav.writeUInt32LE(8000, 24); wav.writeUInt32LE(16000, 28); wav.writeUInt16LE(2, 32); wav.writeUInt16LE(16, 34); wav.write('data', 36); wav.writeUInt32LE(32000, 40);
  const captured = await (await request.post('/api/ingest', { multipart: { session_id: session.session_id, files: { name: 'range-test.wav', mimeType: 'audio/wav', buffer: wav } } })).json();
  const voice = captured.fragments[0];
  // Browser fixture replaces only the provider result. API integration/persistence runs in Python.
  let attempts = 0;
  await page.route('**/api/transcribe', async (route) => {
    expect(route.request().postDataJSON()).toEqual({ source_id: voice.id });
    attempts++;
    await route.fulfill(attempts === 1 ? { status: 503, json: { detail: 'Transcription is temporarily unavailable.' } } : { json: {
      schema_version: '0.1.0', source_ids: [voice.id], duration_ms: 2000,
      segments: [{ text: 'Exact test excerpt.', clip_start_ms: 250, clip_end_ms: 750 }],
    } });
  });
  await page.addInitScript(() => {
    const create = AudioContext.prototype.createBufferSource;
    AudioContext.prototype.createBufferSource = function () {
      const source = create.call(this), start = source.start.bind(source);
      source.start = (when, offset, duration) => { Reflect.set(window, 'lastScheduledExcerpt', { offset, duration }); start(when, offset, duration); };
      return source;
    };
  });
  await page.goto(`/weaving?session=${session.session_id}`);
  await expect(page.locator('.voice-transcript').getByRole('alert')).toContainText('temporarily unavailable');
  await page.getByRole('button', { name: 'Retry transcription' }).click();
  await expect(page.getByText('Exact test excerpt.')).toBeVisible();
  const originalRequest = page.waitForResponse((response) => response.url().endsWith(voice.original_media_ref));
  await page.getByRole('button', { name: 'Play original excerpt 1' }).click();
  expect(await (await originalRequest).body()).toEqual(wav);
  await expect.poll(() => page.evaluate(() => Reflect.get(window, 'lastScheduledExcerpt'))).toEqual({ offset: .25, duration: .5 });
  await expect(page.getByRole('button', { name: 'Play original excerpt 1' })).toBeVisible();
  expect(attempts).toBe(2);
  await expect(page.locator('.voice-transcript').getByRole('alert')).toHaveCount(0);
  await request.delete(`/api/source/${voice.id}`);
});
