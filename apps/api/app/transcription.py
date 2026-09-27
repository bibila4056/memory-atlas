"""Replaceable production STT adapter. Exact segment wording is never rewritten.

OpenAI's whisper-1 verbose_json response supplies segment timestamps; the
application converts seconds to its canonical milliseconds and validates all
ranges before persisting. No model-generated memoir text or fallback transcript.
"""
import os
from typing import Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field

from .transcription_models import TimedTranscript, TranscriptSegment


class TranscriptionUnavailable(Exception):
    pass


class TranscriptionFailed(Exception):
    pass


class TranscriptionAdapter(Protocol):
    def transcribe(self, original: bytes, filename: str, media_type: str) -> TimedTranscript: ...


class ProviderSegment(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    text: str
    start: float = Field(ge=0)
    end: float = Field(gt=0)


class ProviderResponse(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    duration: float = Field(gt=0)
    segments: list[ProviderSegment]


class OpenAITranscriptionAdapter:
    def transcribe(self, original: bytes, filename: str, media_type: str) -> TimedTranscript:
        key = os.getenv('OPENAI_API_KEY')
        if not key:
            raise TranscriptionUnavailable('Voice transcription isn’t connected yet. Your original recording is safely kept.')
        try:
            with httpx.Client(timeout=httpx.Timeout(60, connect=10)) as client:
                response = client.post('https://api.openai.com/v1/audio/transcriptions',
                    headers={'Authorization': f'Bearer {key}'},
                    data={'model': 'whisper-1', 'response_format': 'verbose_json', 'timestamp_granularities[]': 'segment'},
                    files={'file': (filename, original, media_type)})
                response.raise_for_status()
            evidence = ProviderResponse.model_validate(response.json())
            return TimedTranscript(duration_ms=round(evidence.duration * 1000), segments=[
                TranscriptSegment(text=segment.text, clip_start_ms=round(segment.start * 1000), clip_end_ms=round(segment.end * 1000))
                for segment in evidence.segments
            ])
        except (httpx.HTTPError, ValueError) as error:
            # Never surface provider bodies, credentials, or an invalid partial transcript.
            raise TranscriptionFailed('Transcription couldn’t finish. Your recording is kept; please try again.') from error


class LocalWhisperAdapter:
    """Offline speech-to-text with faster-whisper (MIT; CTranslate2 port of OpenAI Whisper).
    Downloads the model once on first use; segment timestamps map to the same exact clip ranges."""

    def __init__(self, model_size: str | None = None):
        try:
            from faster_whisper import WhisperModel
        except ImportError as error:
            raise TranscriptionUnavailable('Local transcription isn’t installed. Run `.venv/bin/pip install faster-whisper`, or add OPENAI_API_KEY to .env.') from error
        self.model = WhisperModel(model_size or os.getenv('MEMORY_ATLAS_WHISPER_MODEL', 'small'), device='cpu', compute_type='int8')

    def transcribe(self, original: bytes, filename: str, media_type: str) -> TimedTranscript:
        import io
        try:
            segments, info = self.model.transcribe(io.BytesIO(original), vad_filter=True)
            segments = [s for s in segments if s.text.strip()]
            duration = max(info.duration, max((s.end for s in segments), default=0.001))
            total, out, previous = round(duration * 1000), [], 0
            for s in segments:  # clamp rounding so ranges stay ordered and inside the recording
                start = max(previous, round(s.start * 1000))
                end = min(total, max(round(s.end * 1000), start + 1))
                if end > start:
                    out.append(TranscriptSegment(text=s.text, clip_start_ms=start, clip_end_ms=end))
                    previous = end
            return TimedTranscript(duration_ms=total, segments=out)
        except (ValueError, RuntimeError, OSError) as error:
            raise TranscriptionFailed('Transcription couldn’t finish. Your recording is kept; please try again.') from error


_local: LocalWhisperAdapter | None = None


def get_transcription_adapter() -> TranscriptionAdapter:
    """openai (key present) → local faster-whisper (installed) → a clear 'not connected' error. MEMORY_ATLAS_STT forces one."""
    global _local
    choice = os.getenv('MEMORY_ATLAS_STT', 'auto')
    if choice == 'openai' or (choice == 'auto' and os.getenv('OPENAI_API_KEY')):
        return OpenAITranscriptionAdapter()
    if _local is None:
        try:
            _local = LocalWhisperAdapter()
        except TranscriptionUnavailable:
            if choice == 'local':
                raise
            return OpenAITranscriptionAdapter()  # raises the friendly "not connected" message on use
    return _local


def ensure_transcripts(session) -> list[dict]:
    """Transcribe every voice clip that has no transcript yet (quietly for 'Play my voice' clips).
    Returns one status row per clip; never raises — the weave simply goes on without the words."""
    from . import capture_store as store
    from .transcription_models import SourceTranscript
    rows, adapter, error = [], None, None
    for fragment in (f for f in session.fragments if f.modality == 'audio'):
        row = {'source_id': str(fragment.id), 'shown_as_text': not fragment.keep_original}
        transcript = fragment.transcript
        if transcript is None and error is None:
            try:
                adapter = adapter or get_transcription_adapter()
                result = adapter.transcribe(store.get_source(fragment.id)[1], fragment.filename or 'voice.webm', fragment.media_type or 'audio/webm')
                transcript = store.save_transcript(fragment.id, SourceTranscript(source_ids=[fragment.id], **result.model_dump()))
            except TranscriptionUnavailable as exc:
                error = ('unavailable', str(exc))
            except (TranscriptionFailed, KeyError, ValueError) as exc:
                row.update(status='failed', detail=str(exc))
                rows.append(row)
                continue
        if transcript is not None:
            row.update(status='transcribed', text=' '.join(s.text.strip() for s in transcript.segments).strip())
        else:
            row.update(status=error[0] if error else 'unavailable', detail=error[1] if error else None)
        rows.append(row)
    return rows
