"""Timestamped evidence in the same millisecond units as resolved audio elements."""
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from .models import ContractModel


class TranscriptSegment(ContractModel):
    text: str = Field(min_length=1)
    clip_start_ms: int = Field(ge=0, strict=True)
    clip_end_ms: int = Field(gt=0, strict=True)

    @model_validator(mode='after')
    def valid_range(self):
        if not self.text.strip() or self.clip_end_ms <= self.clip_start_ms:
            raise ValueError('An excerpt must have words and a positive clip range.')
        return self


class TimedTranscript(ContractModel):
    duration_ms: int = Field(gt=0, strict=True)
    segments: list[TranscriptSegment]

    @model_validator(mode='after')
    def valid_segments(self):
        previous_end = 0
        for segment in self.segments:
            if segment.clip_start_ms < previous_end or segment.clip_end_ms > self.duration_ms:
                raise ValueError('Transcript ranges must be ordered, non-overlapping, and within the recording.')
            previous_end = segment.clip_end_ms
        return self


class SourceTranscript(TimedTranscript):
    schema_version: Literal['0.1.0'] = '0.1.0'
    source_ids: list[UUID] = Field(min_length=1, max_length=1)


class TranscribeRequest(ContractModel):
    source_id: UUID
