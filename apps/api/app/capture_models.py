"""Canonical capture contracts; originals are immutable, presentation directives are editable."""
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field

from .models import ContractModel
from .transcription_models import SourceTranscript


class CreateSession(ContractModel):
    session_id: UUID = Field(default_factory=uuid4)


class ConversationTurn(ContractModel):
    role: Literal['weaver', 'author']
    text: str = Field(min_length=1, max_length=2000)
    source_id: UUID | None = None
    question_id: str | None = None
    at: datetime | None = None


class SourceFragment(ContractModel):
    schema_version: Literal['0.1.0'] = '0.1.0'
    id: UUID
    session_id: UUID
    modality: Literal['image', 'text', 'audio']
    original_media_ref: str | None = None
    original_text: str | None = None
    filename: str | None = None
    media_type: str | None = None
    byte_size: int = 0
    captured_at: datetime | None = None
    keep_original: bool = True
    source_instruction: str | None = None
    transcript: SourceTranscript | None = None


class CaptureSession(ContractModel):
    schema_version: Literal['0.1.0'] = '0.1.0'
    session_id: UUID
    created_at: datetime
    allow_text_refinement: bool = False
    weave_instruction: str | None = Field(default=None, description="Author's optional free-text guidance for the weaver (e.g. 'focus on Shelly').")
    woven: bool = Field(default=False, description='True once a weave has finished for this session; Capture then starts a fresh notebook page.')
    conversation: list[ConversationTurn] = []
    fragments: list[SourceFragment]


class SessionPreferences(ContractModel):
    allow_text_refinement: bool | None = None
    weave_instruction: str | None = Field(default=None, max_length=2000)


class TextEdit(ContractModel):
    text: str = Field(min_length=1, max_length=20000)


class FragmentPreferences(ContractModel):
    keep_original: bool
    source_instruction: str | None = Field(default=None, max_length=4000)
