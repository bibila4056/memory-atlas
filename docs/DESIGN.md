# Memory Atlas — Design Direction

## 1. Design thesis

A premium, human, tactile digital diary:
**editorial journal × artist notebook × quiet museum catalogue**

Avoid:
- generic SaaS dashboards
- bubbly AI chat aesthetics
- scrapbook overload
- excessive stickers
- synthetic "AI fantasy" imagery
- faux-vintage clutter

The experience should feel intimate and crafted.

## 2. Base palette

Primary shell:
- Moss green: `#344A3D`
- Deep moss: `#27382F`
- Aged gold: `#B89A56`
- Warm paper: `#EFE6D3`
- Light paper: `#F7F1E5`
- Ink: `#302B25`
- Muted graphite: `#6D675E`

Exact values may be tuned after visual testing, but the relationships should remain:
deep green + warm aged paper + restrained golden wear.

## 3. Opening cover

Closed diary:
- cloth/leather-like dark green cover
- slightly faded/yellowed page edges
- restrained embossed or aged-gold "Memory Atlas"
- no ornate fantasy-book styling
- believable physical depth and shadow

Animation:
1. cover rests closed
2. slight camera/lighting shift
3. cover opens
4. 1–2 paper pages turn
5. settles into Capture Desk

Duration: ~1–1.3 s.
Only the first entry in a session should require the full animation.

## 4. Default Capture Desk

The first usable page after opening.

Goal: zero intimidation.

Main prompt:
**What do you want to remember today?**

Surface:
- one large quiet input field
- attachment row: Photos · Voice · Text
- dropped fragments appear naturally around/above the composer
- assistant copy stays minimal
- one primary CTA: **Weave this memory**
- secondary navigation tucked into notebook tabs/bookmarks:
  - Capture
  - Memories / Calendar

Do not ask for:
- style
- palette
- narrative type
- template
before the user uploads their memory.

## 5. Weaving State

Weaving must communicate intelligence without becoming a developer console.

Suggested progression:

1. **Fragments**
   - "11 fragments received"
   - visual thumbnails + voice/text counts

2. **Understanding**
   - moments forming from fragments
   - tiny chips: people / objects / phrases / places / moods
   - do not expose the term "Memory Atom" to the user

3. **Selecting**
   - show duplicate merging and chosen story pieces
   - "3 coffee photos → one moment"
   - show why a fragment was selected in one short phrase

4. **Story shape**
   - selected moments with flexible roles
   - e.g. Anchor / Human / Detail / Shift / Closing
   - do not force chronological roles when inappropriate

5. **Art direction**
   - recommended palette
   - visual language
   - treatment badges:
     Preserve / Annotate / Extend / Distill
   - source preservation confirmation

6. **Rendering**
   - subtle page assembly animation

This state can be partially precomputed/cached in the OA demo, but the underlying selection pipeline should be real.

## 6. Palette choice

Palette appears **after** the AI understands the story.

AI recommends one palette derived from:
- dominant photo colors
- emotional tone
- chosen Art Direction Profile

Offer at most 2–3 alternatives.

Examples:
- Moss Journal
- Rain Archive
- Sun-Faded

Changing palette should not replace the entire story or reset the composition.

## 7. Memory Spread

Open notebook, asymmetrical editorial composition.

Rules:
- generous negative space
- one clear visual anchor
- photos should remain recognizable and unfiltered when preserved
- generated assets are sparse
- text hierarchy must be strong
- no more than 1–2 handwritten accents per spread
- exact text rendered deterministically, never baked into generated image assets

Ideal feel:
quietly special, not maximally decorated.

## 8. Artistic element behavior

Examples:
- coffee photo → tiny doodled coffee cup beside it
- flower photo → 1–2 botanical line motifs
- rainy street → optional half-real / half-illustrated extension
- book/library → simple ink-line books as accent
- route/transition → brush line, tape path, or loose arrow

Generated elements should echo the user's source, not introduce unrelated ephemera.

## 9. Provenance UI

Hover/select:
- selected element stays fully opaque
- other elements fade to ~65–75%
- compact source card slides/fades in
- show source thumbnail or audio icon
- expose Original / Refined where relevant
- play voice source inline if feasible

This should feel elegant, not forensic.

## 10. Calendar / Archive

Not the landing page.

A notebook tab or top-level bookmark opens Calendar.

Dates with memories contain a small Memory Stamp.
No dense analytics.
No streaks.
No gamification.

## 11. Motion principles

Motion should imitate paper and physical memory:
- page turn
- fragment drift/settling
- tape/doodle fade-in
- subtle reveal of source links

Avoid:
- bouncing cards
- springy SaaS micro-interactions
- exaggerated parallax
- constant motion

## 12. Demo-specific visual priority

P0 visual polish:
1. cover opening
2. Capture Desk
3. Weaving State
4. final Memory Spread
5. provenance hover

Calendar polish is secondary.
