"""POST /api/weave — one bounded weaving run over preserved sources (D-018). Results are persisted per session."""
import os
from uuid import UUID

from fastapi import APIRouter, HTTPException

from . import capture_store as store
from .capture_routes import lookup
from .weave_models import ClarifyResult, WeaveRequest, WeaveResult

router = APIRouter(prefix='' if os.getenv('VERCEL') else '/api')


def save(result: WeaveResult) -> None:
    with store.connection() as db:
        db.execute('INSERT OR REPLACE INTO weaves VALUES (?, ?)', (str(result.session_id), result.model_dump_json()))


@router.post('/weave', response_model=WeaveResult)
def run_weave(request: WeaveRequest) -> WeaveResult:
    try:
        from .weaver import weave  # lazy: capture must keep working even if the ML extras aren't installed
    except ImportError as error:
        raise HTTPException(503, 'Weaving needs numpy and Pillow: run `.venv/bin/pip install -r apps/api/requirements.txt`, then restart the API. Your originals are safe.') from error
    try:
        result = weave(request.session_id)
    except KeyError as error:
        raise HTTPException(404, 'Notebook not found.') from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    save(result)
    return result


@router.get('/weave/{session_id}', response_model=WeaveResult)
def latest_weave(session_id: UUID) -> WeaveResult:
    with store.connection() as db:
        db.execute('CREATE TABLE IF NOT EXISTS weaves (session_id TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE, result TEXT NOT NULL)')
        row = db.execute('SELECT result FROM weaves WHERE session_id=?', (str(session_id),)).fetchone()
    if row is None:
        raise HTTPException(404, 'This memory has not been woven yet.')
    return WeaveResult.model_validate_json(row[0])


@router.post('/clarify', response_model=ClarifyResult)
def clarify(request: WeaveRequest) -> ClarifyResult:
    """At most two short follow-up questions before weaving (docs/ART_DIRECTION.md §D)."""
    try:
        from .art_director import questions
        from .evidence import extract
        from .reasoning import get_reasoning_provider
        from .weaver import build_atoms
    except ImportError:
        return ClarifyResult(questions=[])  # no questions beats a broken Capture
    try:
        session = store.get_session(request.session_id)
    except KeyError as error:
        raise HTTPException(404, 'Notebook not found.') from error
    from .transcription import ensure_transcripts
    voices = ensure_transcripts(session)          # voice notes are heard before anything is understood
    session = store.get_session(request.session_id)
    evidence = {str(f.id): extract(f, store.get_source(f.id)[1]) for f in session.fragments}
    usable = [ev for ev in evidence.values() if ev.image is not None or ev.text]
    if not any(ev.image is not None for ev in usable):
        return ClarifyResult(questions=[], voices=voices)
    atoms = build_atoms(get_reasoning_provider(usable).atomize(usable), evidence)
    photos = [f for f in session.fragments if f.modality == 'image']
    names = {str(f.id): f'photo {i + 1}' for i, f in enumerate(photos)}
    words = {ev.id: ev.text for ev in evidence.values() if ev.text}
    instructions = {str(f.id): f.source_instruction for f in session.fragments}
    image_atoms = [a for a in atoms if str(a.source_ids[0]) in names]
    asked = {t.question_id for t in session.conversation if t.role == 'author' and t.question_id}
    limit = int(os.getenv('MEMORY_ATLAS_MAX_QUESTIONS', '1'))  # the demo asks one; the rules allow up to 2
    pending = [q for q in questions(image_atoms, words, names, instructions, atoms) if q.id not in asked][:limit]
    seen = [{'source_id': str(a.source_ids[0]), 'captured_at': a.captured_at, 'subject_kind': a.subject_kind, 'people': a.people,
             'labels': list(dict.fromkeys([d.label for d in a.details] + a.objects))[:4]} for a in image_atoms]
    return ClarifyResult(questions=[q.model_dump() for q in pending], photos=seen, voices=voices)


# ── art assets (ADR 0005: live → cache → fallback, always labelled) ─────────
from fastapi.responses import FileResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402


class GenerateAssetRequest(BaseModel):
    session_id: UUID
    source_id: UUID


@router.post('/generate-asset')
def generate_asset(request: GenerateAssetRequest):
    from .art_director import ArtRequest
    from .art_tools import ArtAsset, resolve
    woven = latest_weave(request.session_id)
    art = woven.art.requests if woven.art else []
    match = next((r for r in art if r.source_id == str(request.source_id)), None)
    if match is None:
        raise HTTPException(422, 'This photo has no art treatment in the current weave.')
    atom = next((a for a in woven.atoms if str(a.source_ids[0]) == match.source_id), None)
    subject = ', '.join((atom.objects if atom else [])[:4]) or (atom.event if atom else 'the main subject')
    _, original = lookup(store.get_source, request.source_id)
    asset = resolve(ArtRequest.model_validate(match.model_dump()), original, subject)
    return ArtAsset.model_validate(asset.model_dump()).model_dump()


@router.get('/art/{name}')
def art_file(name: str):
    from .art_tools import art_dir
    path = art_dir() / name
    if '/' in name or '..' in name or not path.is_file():
        raise HTTPException(404, 'Asset not found.')
    return FileResponse(path, media_type='image/png', headers={'Cache-Control': 'private, max-age=3600'})
