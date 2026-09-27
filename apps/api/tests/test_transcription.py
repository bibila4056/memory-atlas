import io
import wave
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.transcription import OpenAITranscriptionAdapter, TranscriptionFailed, get_transcription_adapter
from app.transcription_models import TimedTranscript, TranscriptSegment


def wav_bytes():
    file = io.BytesIO()
    with wave.open(file, 'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(8000)
        wav.writeframes(b'\x00\x00' * 16000)
    return file.getvalue()


class DeterministicAdapter:
    def __init__(self):
        self.calls = []

    def transcribe(self, original, filename, media_type):
        self.calls.append((original, filename, media_type))
        return TimedTranscript(duration_ms=2000, segments=[
            TranscriptSegment(text='  on a rainy day', clip_start_ms=250, clip_end_ms=750),
            TranscriptSegment(text='my exact words. ', clip_start_ms=1000, clip_end_ms=1800),
        ])


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv('MEMORY_ATLAS_DATA_DIR', str(tmp_path))
    adapter = DeterministicAdapter()
    app.dependency_overrides[get_transcription_adapter] = lambda: adapter
    with TestClient(app) as client:
        session = client.post('/api/session', json={}).json()['session_id']
        source = client.post('/api/ingest', data={'session_id': session}, files={'files': ('voice.wav', wav_bytes(), 'audio/wav')}).json()['fragments'][0]
        yield client, adapter, source
    app.dependency_overrides.clear()


def test_api_transcribes_preserved_audio_and_persists_exact_ranges(setup):
    client, adapter, source = setup
    result = client.post('/api/transcribe', json={'source_id': source['id']})
    assert result.status_code == 200
    transcript = result.json()
    assert transcript['source_ids'] == [source['id']]
    assert transcript['segments'][0] == {'text': '  on a rainy day', 'clip_start_ms': 250, 'clip_end_ms': 750}
    assert adapter.calls == [(wav_bytes(), 'voice.wav', 'audio/wav')]
    # A new connection/reload resolves both unchanged evidence and persisted transcription.
    with TestClient(app) as reloaded:
        assert reloaded.get(f"/api/source/{source['id']}").json()['transcript'] == transcript
        assert reloaded.get(source['original_media_ref']).content == wav_bytes()
        assert reloaded.post('/api/transcribe', json={'source_id': source['id']}).json() == transcript
    assert len(adapter.calls) == 1
    client.patch(f"/api/source/{source['id']}", json={'keep_original': False})
    assert client.get(f"/api/source/{source['id']}").json()['transcript'] == transcript
    client.delete(f"/api/source/{source['id']}")
    assert client.post('/api/transcribe', json={'source_id': source['id']}).status_code == 404
    fresh = client.post('/api/ingest', data={'session_id': source['session_id']}, files={'files': ('new.wav', wav_bytes(), 'audio/wav')}).json()['fragments'][0]
    assert fresh['transcript'] is None
    assert fresh['id'] != source['id']


@pytest.mark.parametrize('start,end', [(-1, 100), (100, 100), (200, 100), (100, 2001), (0.5, 100), (0, float('inf'))])
def test_typed_contract_rejects_invalid_or_out_of_range_offsets(start, end):
    with pytest.raises(ValidationError):
        TimedTranscript(duration_ms=2000, segments=[{'text': 'words', 'clip_start_ms': start, 'clip_end_ms': end}])


def test_contract_rejects_overlapping_unordered_and_blank_segments():
    with pytest.raises(ValidationError):
        TimedTranscript(duration_ms=2000, segments=[
            TranscriptSegment(text='first', clip_start_ms=100, clip_end_ms=700),
            TranscriptSegment(text='second', clip_start_ms=600, clip_end_ms=900),
        ])
    with pytest.raises(ValidationError):
        TranscriptSegment(text='  ', clip_start_ms=0, clip_end_ms=1)


def test_missing_key_is_recoverable_and_never_writes_a_fake_transcript(setup, monkeypatch):
    client, _, source = setup
    app.dependency_overrides.clear()
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    assert client.post('/api/transcribe', json={'source_id': source['id']}).status_code == 503
    assert client.get(f"/api/source/{source['id']}").json()['transcript'] is None
    assert client.get(source['original_media_ref']).content == wav_bytes()
    note = client.post('/api/ingest', data={'session_id': source['session_id'], 'text_json': '"text"'}).json()['fragments'][-1]
    assert client.post('/api/transcribe', json={'source_id': note['id']}).status_code == 422
    assert client.post('/api/transcribe', json={'source_id': str(uuid4())}).status_code == 404


def test_production_adapter_sends_original_and_requests_segment_timestamps(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only-placeholder')
    def respond(request):
        assert request.url.path == '/v1/audio/transcriptions'
        body = request.read()
        assert wav_bytes() in body
        assert b'whisper-1' in body and b'verbose_json' in body and b'timestamp_granularities[]' in body
        return httpx.Response(200, json={'duration': 2, 'segments': [{'text': ' exact words ', 'start': .25, 'end': .75}], 'language': 'english'})
    original_client = httpx.Client
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: original_client(transport=httpx.MockTransport(respond), **kwargs))
    result = OpenAITranscriptionAdapter().transcribe(wav_bytes(), 'voice.wav', 'audio/wav')
    assert result.segments[0].text == ' exact words '
    assert result.segments[0].clip_start_ms == 250


@pytest.mark.parametrize('response', [httpx.Response(429, json={'error': 'private provider detail'}), httpx.Response(200, json={'duration': 2, 'segments': [{'text': 'bad', 'start': 1, 'end': 4}]})])
def test_production_adapter_rejects_provider_failure_and_bad_offsets(monkeypatch, response):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only-placeholder')
    original_client = httpx.Client
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: original_client(transport=httpx.MockTransport(lambda request: response), **kwargs))
    with pytest.raises(TranscriptionFailed, match='Your recording is kept'):
        OpenAITranscriptionAdapter().transcribe(wav_bytes(), 'voice.wav', 'audio/wav')


def test_local_whisper_adapter_maps_segments_to_exact_ranges(monkeypatch):
    import sys, types
    from app import transcription
    seg = lambda t, a, b: types.SimpleNamespace(text=t, start=a, end=b)

    class FakeModel:
        def __init__(self, *args, **kwargs): pass
        def transcribe(self, audio, vad_filter):
            return iter([seg(' It was pouring.', 0.0, 1.2004), seg('  ', 1.2, 1.3), seg(' Churros saved us.', 1.1999, 2.5)]), types.SimpleNamespace(duration=2.5)
    monkeypatch.setitem(sys.modules, 'faster_whisper', types.SimpleNamespace(WhisperModel=FakeModel))
    result = transcription.LocalWhisperAdapter().transcribe(b'audio', 'v.wav', 'audio/wav')
    assert [(s.text, s.clip_start_ms, s.clip_end_ms) for s in result.segments] == [(' It was pouring.', 0, 1200), (' Churros saved us.', 1200, 2500)]
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.setattr(transcription, '_local', None)
    assert isinstance(transcription.get_transcription_adapter(), transcription.LocalWhisperAdapter)
