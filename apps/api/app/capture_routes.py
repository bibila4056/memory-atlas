"""Bounded HTTP capture and original-source retrieval; no transcription or weaving here."""
import json
import os
import sqlite3
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from . import capture_store as store
from .capture_models import CaptureSession, CreateSession, FragmentPreferences, SessionPreferences, SourceFragment, TextEdit, ConversationTurn

# Vercel Services mounts this app at /api and strips that prefix. Local uvicorn
# still exposes the same public /api contract directly.
router = APIRouter(prefix='' if os.getenv('VERCEL') else '/api')
MAX_FILE_BYTES = 25 * 1024 * 1024
IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/avif'}
AUDIO_TYPES = {'audio/mpeg', 'audio/mp3', 'audio/mp4', 'audio/x-m4a', 'audio/wav', 'audio/x-wav', 'audio/ogg', 'audio/webm', 'video/webm'}


def lookup(operation, *args):
    try:
        return operation(*args)
    except KeyError as error:
        raise HTTPException(404, str(error)) from error


@router.post('/session', response_model=CaptureSession)
def create_session(request: CreateSession) -> CaptureSession:
    return store.open_session(request.session_id)


@router.get('/session/{session_id}', response_model=CaptureSession)
def get_session(session_id: UUID) -> CaptureSession:
    return lookup(store.get_session, session_id)


@router.patch('/session/{session_id}', response_model=CaptureSession)
def update_session(session_id: UUID, preferences: SessionPreferences) -> CaptureSession:
    return lookup(store.set_preferences, session_id, preferences.allow_text_refinement, preferences.weave_instruction,
                  'weave_instruction' in preferences.model_fields_set)


@router.post('/ingest', response_model=CaptureSession)
async def ingest(session_id: Annotated[UUID, Form()], files: Annotated[list[UploadFile], File()] = [], text_json: Annotated[str | None, Form()] = None) -> CaptureSession:
    # JSON escapes prevent the browser's multipart encoder from rewriting LF to CRLF.
    text = None
    if text_json is not None:
        try:
            text = json.loads(text_json)
        except (ValueError, TypeError) as error:
            raise HTTPException(400, 'The note must be a JSON-encoded string.') from error
        if not isinstance(text, str):
            raise HTTPException(400, 'The note must be a JSON-encoded string.')
    if len(files) > 12:
        raise HTTPException(400, 'Add up to 12 files at a time.')
    if text is not None and (not text.strip() or len(text) > 20000):
        raise HTTPException(400, 'Add a note between 1 and 20,000 characters.')
    if not files and text is None:
        raise HTTPException(400, 'Add a photo, voice clip, or note first.')
    originals = []
    try:
        for file in files:
            media_type = (file.content_type or '').split(';')[0]
            if media_type not in IMAGE_TYPES | AUDIO_TYPES:
                raise HTTPException(415, 'Use JPG, PNG, WebP, GIF, AVIF, or a supported audio file.')
            data = await file.read(MAX_FILE_BYTES + 1)
            if not data or len(data) > MAX_FILE_BYTES:
                raise HTTPException(413, 'Each file must be non-empty and at most 25 MB.')
            originals.append(('image' if media_type in IMAGE_TYPES else 'audio', file.filename or 'Original', media_type, data))
            if sum(len(item[3]) for item in originals) > 100 * 1024 * 1024:
                raise HTTPException(413, 'Add up to 100 MB of originals at a time.')
        return lookup(store.ingest, session_id, originals, text)
    except sqlite3.IntegrityError as error:
        raise HTTPException(409, 'That couldn’t be saved. Everything already in your notebook is kept.') from error
    finally:
        for file in files:
            await file.close()


@router.get('/source/{source_id}', response_model=SourceFragment)
def source(source_id: UUID) -> SourceFragment:
    return lookup(store.get_source, source_id)[0]


@router.patch('/source/{source_id}', response_model=SourceFragment)
def update_source(source_id: UUID, preferences: FragmentPreferences) -> SourceFragment:
    return lookup(store.set_directive, source_id, preferences)


@router.get('/source/{source_id}/media')
def source_media(source_id: UUID) -> Response:
    fragment, original = lookup(store.get_source, source_id)
    return Response(original, media_type=fragment.media_type, headers={'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'private, max-age=31536000, immutable'})


@router.delete('/source/{source_id}', response_model=CaptureSession)
def delete_source(source_id: UUID) -> CaptureSession:
    return lookup(store.delete_source, source_id)


@router.put('/source/{source_id}/text', response_model=SourceFragment)
def edit_text(source_id: UUID, edit: TextEdit) -> SourceFragment:
    try:
        return lookup(store.edit_text, source_id, edit.text)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@router.post('/session/{session_id}/conversation', response_model=CaptureSession)
def add_conversation(session_id: UUID, turns: list[ConversationTurn]) -> CaptureSession:
    return lookup(store.add_turns, session_id, turns)
