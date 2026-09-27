# Sticker library

- `originals/` — the PNGs as supplied (kept for rebuilding).
- `catalog.json` — hand-written meaning: kind, medium, generic, role, tags, moods, notes. **Edit this.**
- `python3 scripts/build_stickers.py` — cleans halos, trims, caps at 1100 px, measures aspect + 3-colour palette → `public/stickers/*.png` and `public/stickers/library.json` (read by `src/lib/sticker-library.ts`).

Adding a sticker: drop `originals/<id>.png` (transparent PNG), add an entry to `catalog.json`, rebuild. Use `generic: true` only for decoration that is fine on colour alone (clouds, stars, pressed flowers, leaves). Anything that names a specific thing (a dish, a bicycle, a face) stays `generic: false`.

Licensing: all stickers were supplied by the author; their source licenses have not been verified. Several look like public-domain vintage scans, others like stock cut-outs. Confirm each source before any public or commercial use.
