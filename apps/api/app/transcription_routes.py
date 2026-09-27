"""One bounded, replayable transcription request over an already-preserved source."""
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from . import capture_store as store
from .capture_routes import lookup
from .transcription import TranscriptionAdapter, TranscriptionFailed, TranscriptionUnavailable, get_transcription_adapter
from .transcription_models import SourceTranscript, TranscribeRequest

router = APIRouter(prefix='' if os.getenv('VERCEL') else '/api')


@router.post('/transcribe', response_model=SourceTranscript)
def transcribe(request: TranscribeRequest, adapter: Annotated[TranscriptionAdapter, Depends(get_transcription_adapter)]) -> SourceTranscript:
    fragment, original = lookup(store.get_source, request.source_id)
    if fragment.modality != 'audio':
        raise HTTPException(422, 'Choose a voice recording to transcribe.')
    if fragment.transcript is not None:
        return fragment.transcript
    try:
        result = adapter.transcribe(original, fragment.filename or 'voice.webm', fragment.media_type or 'audio/webm')
        transcript = SourceTranscript(source_ids=[fragment.id], **result.model_dump())
    except TranscriptionUnavailable as error:
        raise HTTPException(503, str(error)) from error
    except TranscriptionFailed as error:
        raise HTTPException(502, str(error)) from error
    # Re-read inside the transaction: preserve concurrent preferences and respect deletion.
    return lookup(store.save_transcript, fragment.id, transcript)
