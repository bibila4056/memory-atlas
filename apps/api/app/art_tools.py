"""Art Tool Router (ARCHITECTURE.md §2.F, ADR 0005): one bounded image-generation call per ArtRequest.

tape_collage    → make-tape-collage "preserved-photo" transparent motif recipe (vendored, MIT)
doodle          → jiuerli-visual-director verbatim B+ kernel + its three style-authority images (vendored, MIT)
scene_extension → Memory Atlas's own EXTEND prompt (Gathered Scenes itself is not redistributable here)

Every asset resolves in order live → cache → fallback, and the result says which one happened, so
cached art is never presented as live (EVALS E5). Tape and doodle outputs become hand-cut stickers
(`cutout.hand_cut`) that the Visual Director places beside their original photo.
"""
import base64
import hashlib
import io
import os
import re
from pathlib import Path
from typing import Literal

import httpx
from PIL import Image

from .art_director import ArtRequest
from .cutout import hand_cut
from .models import ContractModel

SKILLS = Path(__file__).resolve().parents[1] / 'art_skills'
PROMPTS = Path(__file__).parent / 'art_prompts'
PROMPT_VERSION = 'v1'


def art_dir() -> Path:
    default = Path('/tmp/memory-atlas') if os.getenv('VERCEL') else Path(__file__).parents[1] / 'data'
    base = Path(os.getenv('MEMORY_ATLAS_DATA_DIR', default))
    return base / 'art'


class ArtAsset(ContractModel):
    source_id: str
    tool: Literal['tape_collage', 'doodle', 'scene_extension']
    asset_ref: str | None
    generation_mode: Literal['live', 'cache', 'fallback', 'unavailable']
    detail: str = ''


def _section(markdown: str, heading: str) -> str:
    match = re.search(rf'## {re.escape(heading)}\n(.*?)(?=\n## |\Z)', markdown, re.S)
    return match.group(1) if match else ''


def tape_prompt(subject: str) -> str:
    recipes = (SKILLS / 'make-tape-collage' / 'references' / 'prompt-recipes.md').read_text()
    block = re.search(r'```text\n(Use case: transparent motif generation.*?)```', recipes, re.S).group(1)
    return block.replace('<subject>', subject).replace('<recognizable subject anchors, palette, or mood>', subject)


def doodle_prompt(focal: str) -> str:
    skill = (SKILLS / 'jiuerli-visual-director' / 'SKILL.md').read_text()
    kernel = re.search(r'## Verbatim B\+ prompt kernel\n.*?\n\n(>.*?)(?=\n## )', skill, re.S).group(1)
    kernel = '\n'.join(line.lstrip('> ').rstrip() for line in kernel.splitlines())
    return ('Input roles: image 1 controls subject matter, orientation, placement, scale, depth and overlaps; image 2 controls page '
            'composition, blank-space ratio, color sparsity, unfinishedness and handwriting integration; images 3 and 4 control only '
            'local contour deformation, line clarity, color liveliness and variable line thickness. Never copy content from images 2–4.\n'
            f'Focal forms: {focal}. Secondary forms at visibly lower completion.\n\n{kernel}')


def scene_prompt(notes: str) -> str:
    return (PROMPTS / 'scene_extension.md').read_text().split('\n', 2)[2].replace('{scene_notes}', notes)


def build_call(request: ArtRequest, subject: str) -> tuple[str, list[Path], bool]:
    """→ (prompt, style reference images, transparent background?)"""
    if request.tool == 'tape_collage':
        return tape_prompt(subject), [], True
    if request.tool == 'doodle':
        assets = SKILLS / 'jiuerli-visual-director' / 'assets'
        return doodle_prompt(subject), [assets / 'style-authority-bplus.png', assets / 'line-authority-doodle-01.jpg', assets / 'line-authority-doodle-02.jpg'], False
    return scene_prompt(subject), [], False


class ImageModelUnavailable(Exception):
    pass


class OpenAIImageAdapter:
    """POST /v1/images/edits with the source photo first, style references after it."""

    def __init__(self):
        self.key = os.getenv('MEMORY_ATLAS_IMAGE_API_KEY') or os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('MEMORY_ATLAS_IMAGE_MODEL', 'gpt-image-1')
        self.base = os.getenv('MEMORY_ATLAS_IMAGE_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
        if not self.key:
            raise ImageModelUnavailable('No image-model key configured.')

    def generate(self, source_png: bytes, prompt: str, references: list[Path], transparent: bool, size: str) -> bytes:
        files = [('image[]', ('source.png', source_png, 'image/png'))] + [('image[]', (p.name, p.read_bytes(), 'image/png' if p.suffix == '.png' else 'image/jpeg')) for p in references]
        data = {'model': self.model, 'prompt': prompt, 'size': size, 'quality': 'high', 'background': 'transparent' if transparent else 'opaque', 'output_format': 'png'}
        with httpx.Client(timeout=httpx.Timeout(240, connect=10)) as client:
            response = client.post(f'{self.base}/images/edits', headers={'Authorization': f'Bearer {self.key}'}, data=data, files=files)
            response.raise_for_status()
        return base64.b64decode(response.json()['data'][0]['b64_json'])


def cache_key(source_sha256: str, tool: str) -> str:
    return f'{source_sha256[:16]}-{tool}-{PROMPT_VERSION}'


def resolve(request: ArtRequest, source_bytes: bytes, subject: str, adapter_factory=OpenAIImageAdapter, live: bool = True) -> ArtAsset:
    """live → cache → fallback. The live result is post-processed and cached for the next run."""
    sha = hashlib.sha256(source_bytes).hexdigest()
    folder = art_dir()
    folder.mkdir(parents=True, exist_ok=True)
    name = cache_key(sha, request.tool)
    final = folder / f'{name}.png'
    if live:
        try:
            adapter = adapter_factory()
            img = Image.open(io.BytesIO(source_bytes)).convert('RGB')
            img.thumbnail((1536, 1536))
            buffer = io.BytesIO()
            img.save(buffer, 'PNG')
            prompt, refs, transparent = build_call(request, subject)
            raw = adapter.generate(buffer.getvalue(), prompt, refs, transparent, '1024x1536')
            out = Image.open(io.BytesIO(raw)).convert('RGBA')
            if request.placement == 'beside_original':
                out = hand_cut(out)  # sticker: irregular hand-cut paper edge
            out.save(final)
            return ArtAsset(source_id=request.source_id, tool=request.tool, asset_ref=f'/api/art/{final.name}', generation_mode='live')
        except ImageModelUnavailable as error:
            detail = str(error)
        except (httpx.HTTPError, KeyError, ValueError, OSError) as error:
            detail = f'Live generation failed ({type(error).__name__}); your original is untouched.'
    else:
        detail = 'Live generation skipped.'
    if final.exists():
        return ArtAsset(source_id=request.source_id, tool=request.tool, asset_ref=f'/api/art/{final.name}', generation_mode='cache', detail=detail)
    fallback = folder / f'{name}.fallback.png'
    if fallback.exists():
        return ArtAsset(source_id=request.source_id, tool=request.tool, asset_ref=f'/api/art/{fallback.name}', generation_mode='fallback', detail=detail)
    return ArtAsset(source_id=request.source_id, tool=request.tool, asset_ref=None, generation_mode='unavailable', detail=detail)
