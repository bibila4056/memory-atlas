# Memory Atlas — 48-Hour MVP

## Goal

Demonstrate one end-to-end vertical slice:

**messy multimodal fragments → intelligent selection → coherent visual plan → beautiful grounded interactive memoir**

The MVP is successful if it proves both:
1. real AI reasoning/selection
2. polished consumer experience

## Demo input

Prepare one strong example day/experience:
- 8–10 photos
- 1 short voice note (10–20 s)
- 1 messy note or diary fragment

Do not depend on users supplying perfect demo data.

## P0 — must ship

1. Diary cover opening animation
2. Minimal Capture Desk as the default landing experience
3. Upload/add images, text, and one voice clip
4. Voice transcription
5. Typed Memory Atom extraction
6. Moment grouping
7. Bundle Weaver selection with flexible narrative roles
8. Recommended color palette after weaving
9. Structured Visual Plan
10. Deterministic interactive Memory Spread
11. Provenance hover/select for at least:
    - one original photo
    - one voice-derived quote
    - one AI-generated/derived artistic element
12. One real runtime art tool or bounded generative transformation

## P1 — ship if P0 is stable

- Calendar/Archive shell
- Memory Stamp for the demo date
- second art tool
- two alternate palette choices
- optional drag/reposition for memoir elements
- export still image

## P2 — explicitly out of scope

- authentication
- cloud database
- long-term archive search
- Echoes across dates
- Parallel Day / social sharing
- Style DNA learning
- fine-tuning
- multi-user collaboration
- full mobile app
- three-plus real art integrations
- automatic map/location integrations
- music integrations
- fully general generative UI
- production privacy/security infrastructure

## Acceptance criteria

### Capture
- User can understand how to start without onboarding.
- No visual-style choices are required before upload.
- User reaches Weaving in <30 seconds in the demo.

### Weaving
- System visibly groups raw fragments into moments.
- At least one redundant/duplicate fragment is excluded or merged.
- Selected story uses complementary moments, not simply top image similarity.
- Color palette is proposed only after understanding/selection.

### Spread
- At least 60% of the visual evidence is original user material.
- User text shown as original must be verbatim.
- Full page is not a single generated bitmap.
- At least one artistic asset is source-grounded.
- Timeline appears only if it helps this story.

### Provenance
- Every hero/supporting photo on the demo page has a source ID.
- Voice-derived quote links to the original audio.
- AI-derived asset exposes its source and treatment.

### Demo reliability
- Recorded flow must work without waiting for live image generation.
- Cached fallback assets exist.
- One deterministic test fixture can reproduce the full final spread.

## Build order

1. repo/docs/typed schemas
2. visual shell with mocked data
3. transcription
4. Memory Atom extraction
5. moment grouping + bundle selection
6. Visual Plan
7. interactive renderer
8. one art tool
9. provenance
10. Calendar shell
11. polish
12. record demo
