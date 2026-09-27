"""Sticker selection (docs/ART_DIRECTION.md §E) — rules first, scored, explainable.

The library (apps/web/public/stickers/library.json, built from stickers/catalog.json) describes every
sticker: kind, medium, content tags, moods, palette, and whether it is `generic` decoration.

Eligibility
  • content match: the sticker's content tags overlap the story's own words (moods count too, at half weight,
    but only for generic decoration — a mood alone never pulls in a specific thing) (keywords, objects, themes,
    moods, places, moment titles, the author's notes and voice)
  • colour fit: only `generic` stickers may join on colour alone, when their palette sits within
    ΔE≈60 of the spread palette (fit ≥ 0.62). Specific things always need a content match.
Diversity: one per kind, at most one photographic sticker, at most MAX_STICKERS per spread.
Every candidate keeps its score and a one-line reason, so the Weaving screen can show why.
"""
import json
import math
import re
from functools import lru_cache
from pathlib import Path

from .models import ContractModel

LIBRARY = Path(__file__).resolve().parents[2] / 'web' / 'public' / 'stickers' / 'library.json'
MAX_STICKERS, COLOR_FIT_MIN = 3, 0.62


class StickerPick(ContractModel):
    id: str
    label: str
    src: str
    kind: str
    chosen: bool
    score: float
    matched: list[str]
    color_fit: float
    reason: str


@lru_cache(maxsize=1)
def library() -> list[dict]:
    return json.loads(LIBRARY.read_text())['stickers'] if LIBRARY.exists() else []


def _lab(hex_color: str) -> tuple[float, float, float]:
    c = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c]
    xyz = [(c[0] * 0.4124 + c[1] * 0.3576 + c[2] * 0.1805) / 0.95047, c[0] * 0.2126 + c[1] * 0.7152 + c[2] * 0.0722,
           (c[0] * 0.0193 + c[1] * 0.1192 + c[2] * 0.9505) / 1.08883]
    x, y, z = [t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116 for t in xyz]
    return 116 * y - 16, 500 * (x - y), 200 * (y - z)


def color_fit(sticker: dict, palette: list[str]) -> float:
    if not palette:
        return 0.0
    targets = [_lab(p) for p in palette]
    d = sum(p['share'] * min(math.dist(_lab(p['hex']), t) for t in targets) for p in sticker['palette'])
    return max(0.0, 1 - d / 60)


def story_words(texts: list[str]) -> set[str]:
    return {w for t in texts for w in re.findall(r'[a-z]+', t.lower())}


def pick(texts: list[str], palette: list[str], max_stickers: int = MAX_STICKERS) -> list[StickerPick]:
    words = story_words(texts)
    rows = []
    for s in library():
        tag_hits = [t for t in s['tags'] if t in words]
        mood_hits = [t for t in s['moods'] if t in words and t not in tag_hits] if s['generic'] else []  # moods alone never pull in a specific thing
        hits, fit = tag_hits + mood_hits, color_fit(s, palette)
        eligible = bool(hits) or (s['generic'] and fit >= COLOR_FIT_MIN)
        rows.append((s, hits, fit, eligible, len(tag_hits) + 0.5 * len(mood_hits) + fit * 0.8, bool(tag_hits)))
    # Something the story actually contains always outranks a mood or colour match.
    rows.sort(key=lambda r: (not r[3], not r[5], -r[4], r[0]['id']))
    kinds, photographic, taken, out = set(), 0, 0, []
    for s, hits, fit, eligible, score, _ in rows:
        photo = 'photo' in s['medium']
        blocked = ('not part of this story' if not s['generic'] else 'colours don’t match the page') if not eligible else \
            'already have one like it' if s['kind'] in kinds else 'too close to your real photos' if photo and photographic else \
            'one is enough' if taken >= max_stickers else None
        if not blocked:
            taken += 1
            kinds.add(s['kind'])
            photographic += photo
        reason = blocked or (f"echoes “{', '.join(hits[:3])}”" if hits else f'colours already on the page ({round(fit * 100)}%)')
        out.append(StickerPick(id=s['id'], label=s['label'], src=s['src'], kind=s['kind'], chosen=not blocked, score=round(score, 3),
                               matched=hits, color_fit=round(fit, 3), reason=reason))
    return out
