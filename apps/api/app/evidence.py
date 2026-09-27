"""Deterministic evidence extraction from preserved originals (never modifies bytes).

- capture time from EXIF DateTimeOriginal (no invented time when absent)
- exact duplicates via SHA-256 of the original bytes
- perceptual near-duplicates via a 64-bit difference hash (dHash)
- a small display-independent thumbnail for embeddings and palette extraction
"""
import hashlib
import io
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
from PIL import Image, ImageOps

from .capture_models import SourceFragment

EXIF_IFD, DATETIME_ORIGINAL, DATETIME = 0x8769, 36867, 306


@dataclass
class Evidence:
    fragment: SourceFragment
    original: bytes
    sha256: str
    captured_at: datetime | None = None
    image: Image.Image | None = None  # oriented RGB copy, ≤ 512 px; the original bytes stay untouched
    dhash: int | None = None
    text: str | None = None
    extra: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        return str(self.fragment.id)


def exif_time(img: Image.Image) -> datetime | None:
    exif = img.getexif()
    raw = exif.get_ifd(EXIF_IFD).get(DATETIME_ORIGINAL) or exif.get(DATETIME)
    try:
        return datetime.strptime(str(raw).strip(), '%Y:%m:%d %H:%M:%S') if raw else None
    except ValueError:
        return None


def dhash(img: Image.Image, size: int = 8) -> int:
    gray = np.asarray(img.convert('L').resize((size + 1, size), Image.LANCZOS), dtype=np.int16)
    bits = (gray[:, 1:] > gray[:, :-1]).flatten()
    return int(''.join('1' if b else '0' for b in bits), 2)


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count('1')


def extract(fragment: SourceFragment, original: bytes) -> Evidence:
    ev = Evidence(fragment, original, hashlib.sha256(original).hexdigest())
    if fragment.modality == 'image':
        with Image.open(io.BytesIO(original)) as raw:
            ev.captured_at = exif_time(raw)
            raw.draft('RGB', (1024, 1024))  # fast JPEG downscale on decode; the stored original is untouched
            img = ImageOps.exif_transpose(raw).convert('RGB')
        img.thumbnail((512, 512))
        ev.image, ev.dhash = img, dhash(img)
    elif fragment.modality == 'text':
        ev.text = fragment.original_text
    elif fragment.modality == 'audio' and fragment.transcript is not None:
        ev.text = ' '.join(segment.text.strip() for segment in fragment.transcript.segments)
    return ev


def palette(images: list[Image.Image], k: int = 5, seed: int = 3) -> list[str]:
    """k-means over pixels of the *selected* photos → a palette proposed only after selection."""
    if not images:
        return ['#f4eee0', '#6f8193', '#b8543f']
    pixels = np.concatenate([np.asarray(img.resize((64, 64))).reshape(-1, 3) for img in images]).astype(float)
    rng = np.random.default_rng(seed)
    centers = pixels[rng.choice(len(pixels), k, replace=False)]
    for _ in range(12):
        labels = ((pixels[:, None, :] - centers[None]) ** 2).sum(-1).argmin(1)
        centers = np.array([pixels[labels == i].mean(0) if (labels == i).any() else centers[i] for i in range(k)])
    counts = np.bincount(labels, minlength=k)
    ordered = centers[np.argsort(-counts)]
    # Soften toward paper so the palette reads as ink on paper, not a screen swatch.
    paper = np.array([244, 238, 224])
    ordered = ordered * 0.85 + paper * 0.15
    return ['#%02x%02x%02x' % tuple(int(c) for c in color) for color in ordered]
