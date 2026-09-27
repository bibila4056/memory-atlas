"""Local, transactional capture storage. SQLite retains exact source bytes across reload/restart."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import json

from .capture_models import CaptureSession, ConversationTurn, FragmentPreferences, SourceFragment


def database_path() -> Path:
    default = Path('/tmp/memory-atlas') if os.getenv('VERCEL') else Path(__file__).parents[1] / 'data'
    return Path(os.getenv('MEMORY_ATLAS_DATA_DIR', default)) / 'capture.sqlite3'


@contextmanager
def connection():
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=10) as db:
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, allow_refinement INTEGER NOT NULL DEFAULT 0)')
        db.execute('CREATE TABLE IF NOT EXISTS fragments (id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id), modality TEXT NOT NULL, metadata TEXT NOT NULL, original BLOB)')
        # Any number of notes and voice clips (D-030): drop the old one-of-each constraint on existing databases.
        db.execute('DROP INDEX IF EXISTS single_text_or_audio')
        columns = {row[1] for row in db.execute('PRAGMA table_info(sessions)')}
        if 'weave_instruction' not in columns:
            db.execute('ALTER TABLE sessions ADD COLUMN weave_instruction TEXT')
        if 'conversation' not in columns:
            db.execute("ALTER TABLE sessions ADD COLUMN conversation TEXT NOT NULL DEFAULT '[]'")
        db.execute('CREATE TABLE IF NOT EXISTS weaves (session_id TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE, result TEXT NOT NULL)')
        yield db


def read_session(db, session_id: UUID) -> CaptureSession:
    row = db.execute('SELECT created_at, allow_refinement, weave_instruction, conversation FROM sessions WHERE id=?', (str(session_id),)).fetchone()
    if row is None:
        raise KeyError('Session not found')
    fragments = [SourceFragment.model_validate_json(row[0]) for row in db.execute('SELECT metadata FROM fragments WHERE session_id=? ORDER BY rowid', (str(session_id),))]
    return CaptureSession(session_id=session_id, created_at=row[0], allow_text_refinement=bool(row[1]), weave_instruction=row[2],
                          conversation=[ConversationTurn.model_validate(t) for t in json.loads(row[3] or '[]')],
                          woven=db.execute('SELECT 1 FROM weaves WHERE session_id=?', (str(session_id),)).fetchone() is not None, fragments=fragments)


def open_session(session_id: UUID) -> CaptureSession:
    with connection() as db:
        db.execute('INSERT OR IGNORE INTO sessions(id, created_at) VALUES (?, ?)', (str(session_id), datetime.now(timezone.utc).isoformat()))
        return read_session(db, session_id)


def get_session(session_id: UUID) -> CaptureSession:
    with connection() as db:
        return read_session(db, session_id)


def ingest(session_id: UUID, files: list[tuple[str, str, str, bytes]], text: str | None) -> CaptureSession:
    with connection() as db:
        read_session(db, session_id)
        items = files + ([('text', '', 'text/plain', text.encode('utf-8'))] if text is not None else [])
        for modality, filename, media_type, original in items:
            source_id = uuid4()
            fragment = SourceFragment(id=source_id, session_id=session_id, modality=modality,
                original_text=text if modality == 'text' else None,
                original_media_ref=f'/api/source/{source_id}/media' if modality != 'text' else None,
                filename=filename or None, media_type=media_type, byte_size=len(original))
            db.execute('INSERT INTO fragments VALUES (?, ?, ?, ?, ?)',
                       (str(source_id), str(session_id), modality, fragment.model_dump_json(), original))
        return read_session(db, session_id)


def set_preferences(session_id: UUID, allowed: bool | None, instruction: str | None, instruction_set: bool) -> CaptureSession:
    with connection() as db:
        read_session(db, session_id)
        if allowed is not None:
            db.execute('UPDATE sessions SET allow_refinement=? WHERE id=?', (allowed, str(session_id)))
        if instruction_set:
            db.execute('UPDATE sessions SET weave_instruction=? WHERE id=?', ((instruction or '').strip() or None, str(session_id)))
        return read_session(db, session_id)


def edit_text(source_id: UUID, text: str) -> SourceFragment:
    """The author revising their own note. The note is still theirs, so the stored original becomes the new wording."""
    with connection() as db:
        row = db.execute('SELECT metadata FROM fragments WHERE id=?', (str(source_id),)).fetchone()
        if row is None:
            raise KeyError('Source not found')
        fragment = SourceFragment.model_validate_json(row[0])
        if fragment.modality != 'text':
            raise ValueError('Only notes can be edited.')
        data = text.encode('utf-8')
        fragment = fragment.model_copy(update={'original_text': text, 'byte_size': len(data)})
        db.execute('UPDATE fragments SET metadata=?, original=? WHERE id=?', (fragment.model_dump_json(), data, str(source_id)))
        return fragment


def get_source(source_id: UUID) -> tuple[SourceFragment, bytes]:
    with connection() as db:
        row = db.execute('SELECT metadata, original FROM fragments WHERE id=?', (str(source_id),)).fetchone()
        if row is None:
            raise KeyError('Source not found')
        return SourceFragment.model_validate_json(row[0]), row[1]


def set_directive(source_id: UUID, preferences: FragmentPreferences) -> SourceFragment:
    with connection() as db:
        row = db.execute('SELECT metadata FROM fragments WHERE id=?', (str(source_id),)).fetchone()
        if row is None:
            raise KeyError('Source not found')
        fragment = SourceFragment.model_validate_json(row[0]).model_copy(update=preferences.model_dump(exclude_unset=True))
        db.execute('UPDATE fragments SET metadata=? WHERE id=?', (fragment.model_dump_json(), str(source_id)))
        return fragment


def delete_source(source_id: UUID) -> CaptureSession:
    """Only an explicit author deletion removes an original and frees its capture slot."""
    with connection() as db:
        row = db.execute('SELECT session_id FROM fragments WHERE id=?', (str(source_id),)).fetchone()
        if row is None:
            raise KeyError('Source not found')
        db.execute('DELETE FROM fragments WHERE id=?', (str(source_id),))
        return read_session(db, UUID(row[0]))



def save_transcript(source_id: UUID, transcript):
    with connection() as db:
        row = db.execute('SELECT metadata FROM fragments WHERE id=?', (str(source_id),)).fetchone()
        if row is None:
            raise KeyError('Source not found')
        fragment = SourceFragment.model_validate_json(row[0])
        if fragment.transcript is not None:
            return fragment.transcript
        if transcript.source_ids != [source_id] or fragment.modality != 'audio':
            raise ValueError('Transcript must belong to its original voice source.')
        fragment = fragment.model_copy(update={'transcript': transcript})
        db.execute('UPDATE fragments SET metadata=? WHERE id=?', (fragment.model_dump_json(), str(source_id)))
        return transcript


def add_turns(session_id: UUID, turns: list[ConversationTurn]) -> CaptureSession:
    """Append to the author ↔ weaver conversation; it is kept with the session and shown again on reload."""
    with connection() as db:
        session = read_session(db, session_id)
        now = datetime.now(timezone.utc)
        kept = session.conversation + [t.model_copy(update={'at': t.at or now}) for t in turns]
        db.execute('UPDATE sessions SET conversation=? WHERE id=?', (json.dumps([t.model_dump(mode='json') for t in kept]), str(session_id)))
        return read_session(db, session_id)
