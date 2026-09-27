# Memory Atlas — local desktop prototype

This is a fixture-backed composition study at **http://localhost:3000/memories/demo**.
The root route now opens a diary into the persistent Capture Desk (Issue #3).

## Run locally

From the repository root (Node 22+ and Python 3.11+):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r apps/api/requirements.txt
npm ci --cache /private/tmp/memory-atlas-npm-cache
npm run dev:api
```

In a second terminal:

```sh
npm run dev:web
```

`MEMORY_ATLAS_API_URL` optionally changes the server-side API origin (default `http://127.0.0.1:8000`).
Development and production use Next.js’s supported webpack bundler; Turbopack could not create its local worker process in this environment.

The browser receives the validated plan through the Next.js server route; it needs no backend credentials or public environment variables.

## Contract and checks

Pydantic in `api/app/models.py` and `api/app/capture_models.py` is canonical. After changing it, regenerate and retain both OpenAPI and the generated frontend declarations:

```sh
npm run contracts:generate
npm test
npm run lint
npm run build
npx playwright install chromium
npm run test:e2e
```

The end-to-end test starts local servers when needed, fetches the real API plan, checks exact text and provenance attributes, compares normalized geometry at desktop/laptop sizes, exercises desktop zoom, scroll, and fit, and verifies the photo is served byte-for-byte. Screenshots go to `artifacts/issue-2/`.

## Deliberate checkpoint boundaries

- The existing flower-market image is a **synthetic temporary source fixture**, not approved memoir content or final art direction. The words and botanical fallback are sample content too. No live reasoning or art generation runs.
- The renderer uses distinct HTML text/image layers in a fixed 1600 × 1000 coordinate system. Only the outer viewport scales; element geometry never reflows.
- Fixed, repeating SVG grain, a gentle gutter, folios, and paper mounts are renderer chrome with no source provenance. Source-derived elements retain their IDs.
- Masks use normalized polygon points, local pixel SVG paths, or immutable alpha-mask references. Bounds remain the validation geometry.
- The spread fixture uses a tiny local asset registry. Capture now supports original-source lookup, ingest, and voice playback; interactive spread Source Cards remain a later ticket. Issue #4 adds transcription at the Weaving entry.
- Desktop is the current delivery target. **Fit spread** shows the complete composition; **Actual size** allows scrolling at canonical scale. Mobile layout, gestures, and browser acceptance are deferred at the author’s request on 2026-09-26 to protect the remaining sub-24-hour schedule. Earlier mobile screenshots are historical checkpoints, not current acceptance evidence.
- The new cover uses a provisional clay color controlled by `--cover-clay`. Sound remains deferred.


## Issue #3: Capture and preservation

- `/`: closed diary → 1.45-second continuous cover/two-page opening → Capture Desk. The opening is skipped during ordinary in-tab navigation; reduced-motion activation opens directly.
- Add multiple photos, one exact text fragment, and one uploaded or microphone-recorded voice fragment. `Keep original` defaults on; refinement defaults off. Inline Keep original controls persist independently of originals. Hover cards to reveal Delete; click a photo to inspect untouched pixels at original size. Deleting voice or text frees its capture slot. Per-photo instruction and refinement menus were removed at the author’s request.
- Browser local storage holds the active session ID and unfinished text draft. SQLite at `apps/api/data/capture.sqlite3` holds metadata, exact text, and unchanged original file bytes. This folder is ignored by Git. `MEMORY_ATLAS_DATA_DIR` overrides it for tests.
- `/api/session`, `/api/ingest`, and `/api/source/{id}` use Pydantic/OpenAPI. Ingest is multipart with `session_id`, repeated `files`, and optional `text_json` (a JSON-encoded string, to avoid multipart newline normalization). Limits: 12 files / 100 MB per batch, 25 MB per file, 20,000 text characters.
- Import time is not represented as a source's capture time. `captured_at` remains unset until evidence supplies it; untouched file metadata is retained in the original.
- `/weaving?session=…` is a real saved-session handoff with a clearly labeled preview checkpoint. It does not claim AI processing has run. Voice transcription runs here when a voice fragment is present; semantic selection and composition remain subsequent tickets.
- Browser tests exercise eight photo uploads plus note and audio, exact-byte retrieval, preference persistence, reload recovery, opening non-replay, reduced motion, and real MediaRecorder behavior with a fake test microphone. The prepared automated flow must reach the Weaving entry within 30 seconds.

### Author-supplied rainy-day demo

The four supplied photos are retained unchanged in `apps/api/data/demo-rainy-day/`. The demo note is the author's exact phrase, **on a rainy day**. No voice or additional memoir prose has been invented.

After placing those private originals locally, `.venv/bin/python scripts/prepare_rainy_day_demo.py` idempotently prepares the session. Open:

http://localhost:3000/?session=a74738d4-cd11-4c26-93e0-4bfb3c7fe469

Issue #3 screenshots are in `artifacts/issue-3/`. They contain the supplied demo photos; no screenshots or originals have been published or committed.

## Issue #4: Timestamped voice evidence

- `POST /api/transcribe` accepts a stable `source_id`. A replaceable production adapter sends the unchanged recording to OpenAI `whisper-1` with `verbose_json` segment timestamps. Pydantic rejects invalid, overlapping, unordered, or out-of-duration ranges. Seconds become the same integer milliseconds used by resolved audio elements.
- Segment text stays exactly as returned by speech recognition; it is not rewritten or treated as author-verified. Every transcript retains `source_ids`, is stored beside the original, and resolves through `/api/source/{id}` and session reload. Existing transcripts are reused without another provider call.
- `/weaving?session=…` displays the excerpt and **Hear original**. Web Audio decodes the preserved recording, independently checks the actual decoded duration, and schedules precisely the selected start and duration on the audio clock. A new excerpt stops the previous one; leaving the page stops playback.
- Put `OPENAI_API_KEY` in the ignored repository-root `.env` (or backend process environment), then restart the API. No browser credential is used. If credentials/provider are unavailable, the original stays intact and the interface offers Retry transcription; there is no fabricated fallback.
- Deterministic API tests replace the provider adapter and exercise ingest → transcription → reload → exact source retrieval → deletion. HTTP transport tests cover the real adapter's request shape and invalid provider responses without network calls. Browser tests use a clearly isolated transcript fixture with real original audio to verify exact scheduled clip bounds and retry.
- Live provider transcription has **not** been exercised locally because no backend key is configured. The implementation and deterministic tests are complete; live verification remains pending configuration.
- Provider request format reference: [OpenAI speech-to-text guide](https://developers.openai.com/api/docs/guides/speech-to-text).

## Weaving: BundleWeaver-lite (`POST /api/weave`)

Pipeline (`apps/api/app/`): `evidence.py` (EXIF time, SHA-256, dHash, thumbnails) → `reasoning.py` atomize → `embeddings.py` → `weaver.py` duplicate groups → Moments → story reframing → role-conditioned retrieval (top-3 per role) → two diverse seeds → missing-role expansion by weighted marginal gain → one whole-bundle verification with ≤1 validated replacement → palette from the selected photos → persisted `WeaveResult` (`GET /api/weave/{session_id}`). Every result records which providers actually ran (D-026).

Mechanism and citation: Shan et al., *Weaving Visual Narratives: Agentic Image Bundle Composition Beyond Atomic Visual Matching* (arXiv:2608.28695). This is a small-scale adaptation, not a reproduction: no beam search, no spatiotemporal pruning, no IBCBench-scale evaluation.

Install and run:

```bash
.venv/bin/pip install -r apps/api/requirements.txt            # adds numpy + pillow
.venv/bin/pip install -r apps/api/requirements-ml.txt         # optional: real SigLIP 2 (first run downloads ~1.5 GB of weights)
```

Environment (root `.env`, never committed):

| variable | meaning |
|---|---|
| `MEMORY_ATLAS_REASONING_MODEL` | model id for live reasoning (Terra per D-019) |
| `MEMORY_ATLAS_REASONING_BASE_URL` | OpenAI-compatible base URL (default `https://api.openai.com/v1`) |
| `MEMORY_ATLAS_REASONING_API_KEY` | falls back to `OPENAI_API_KEY` |
| `MEMORY_ATLAS_REASONING` | `auto` (default: live → fixture → heuristic), or force one mode |
| `MEMORY_ATLAS_EMBEDDINGS` | `auto` (default: SigLIP 2 if installed, else fallback), `siglip2`, or `fallback` |

Verification status: the SigLIP 2 adapter was exercised with transformers 5.17 against a randomly initialised `Siglip2Model` and the real `Siglip2ImageProcessor` (shapes, NaFlex inputs, normalisation). The pretrained weights and a live reasoning call have **not** been run in the build environment (no network access to Hugging Face or the model API). The live adapter's request shape and ID validation are covered by a mocked-transport test.

## Evaluation E1 (`scripts/eval_bundle.py`)

Point-wise baseline vs BundleWeaver-lite on three labelled cases built from the rainy-day originals plus re-encoded burst frames (`evals/bundle_cases.json`). Results are written to `evals/results/`. See `evals/RESULTS.md`.

## Art direction and the Art Tool Router

- Rules: `docs/ART_DIRECTION.md` → `apps/api/app/art_director.py`. Each `WeaveResult` now carries `art.requests` (tool per selected photo + placement) and `art.annotations` (arrows grounded in the author's words and a detected box).
- `POST /api/clarify {session_id}` returns at most 2 follow-up questions (e.g. "Is that Shelly in photo 3?"). Store the answer with `PATCH /api/source/{id}` as `source_instruction`; the next weave treats it as author evidence.
- `POST /api/generate-asset {session_id, source_id}` resolves one art asset live → cache → fallback via `app/art_tools.py`. Env: `MEMORY_ATLAS_IMAGE_MODEL` (default `gpt-image-1`), `MEMORY_ATLAS_IMAGE_API_KEY` (falls back to `OPENAI_API_KEY`), `MEMORY_ATLAS_IMAGE_BASE_URL`. Assets are served from `GET /api/art/{name}` and stored in the gitignored `apps/api/data/art/`.
- `scripts/seed_art_fallbacks.py` registers the earlier rainy-day art as labelled *fallbacks* so the demo completes offline.
- Vendored skills: `apps/api/art_skills/` (see its README for licenses).
