import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('MEMORY_ATLAS_DATA_DIR', str(tmp_path))
    with TestClient(app) as client:
        yield client


def create(client):
    return client.post('/api/session', json={}).json()['session_id']


def test_reload_preserves_sources_and_defaults(client):
    session_id = create(client)
    original_photo = b'photo-original-with-metadata'
    original_audio = b'audio-original'
    exact_text = '  on a rainy day\nmy words, unchanged.  '
    response = client.post('/api/ingest', data={'session_id': session_id, 'text_json': json.dumps(exact_text)}, files=[
        ('files', ('photo.jpg', original_photo, 'image/jpeg')),
        ('files', ('voice.webm', original_audio, 'audio/webm')),
    ])
    assert response.status_code == 200
    captured = response.json()
    assert captured['allow_text_refinement'] is False
    assert all(fragment['keep_original'] for fragment in captured['fragments'])
    assert len({fragment['id'] for fragment in captured['fragments']}) == 3
    with TestClient(app) as reloaded_client:
        reloaded = reloaded_client.get(f'/api/session/{session_id}').json()
        assert reloaded == captured
        for fragment, original in zip(reloaded['fragments'], [original_photo, original_audio, exact_text.encode()]):
            assert reloaded_client.get(f"/api/source/{fragment['id']}/media").content == original
        assert reloaded['fragments'][2]['original_text'] == exact_text


def test_directives_never_modify_originals(client):
    session_id = create(client)
    captured = client.post('/api/ingest', data={'session_id': session_id, 'text_json': json.dumps('my exact words')}).json()
    source_id = captured['fragments'][0]['id']
    updated = client.patch(f'/api/source/{source_id}', json={'keep_original': False, 'source_instruction': 'Keep the rainy feeling.'})
    assert updated.status_code == 200
    session = client.patch(f'/api/session/{session_id}', json={'allow_text_refinement': True}).json()
    assert session['allow_text_refinement'] is True
    assert session['fragments'][0]['original_text'] == 'my exact words'
    assert session['fragments'][0]['source_instruction'] == 'Keep the rainy feeling.'
    assert client.get(f'/api/source/{source_id}/media').content == b'my exact words'
    assert client.patch(f'/api/source/{source_id}', json={'keep_original': True, 'original_text': 'replacement'}).status_code == 422


def test_any_number_of_notes_and_voice_clips_and_notes_are_editable(client):
    session_id = create(client)
    client.post('/api/ingest', data={'session_id': session_id, 'text_json': json.dumps('first note')})
    client.post('/api/ingest', data={'session_id': session_id, 'text_json': json.dumps('second note')})
    voices = [('files', ('a.wav', b'one', 'audio/wav')), ('files', ('b.wav', b'two', 'audio/wav'))]
    session = client.post('/api/ingest', data={'session_id': session_id}, files=voices).json()
    assert [f['modality'] for f in session['fragments']] == ['text', 'text', 'audio', 'audio']
    note = session['fragments'][0]['id']
    edited = client.put(f'/api/source/{note}/text', json={'text': 'first note, revised'}).json()
    assert edited['original_text'] == 'first note, revised'
    assert client.get(f'/api/source/{note}/media').content == b'first note, revised'
    assert client.put(f"/api/source/{session['fragments'][2]['id']}/text", json={'text': 'x'}).status_code == 422
    session = client.patch(f'/api/session/{session_id}', json={'weave_instruction': '  Focus on Shelly.  '}).json()
    assert session['weave_instruction'] == 'Focus on Shelly.' and session['allow_text_refinement'] is False


def test_session_creation_is_idempotent_and_invalid_uploads_do_not_persist(client):
    session_id = str(uuid4())
    first = client.post('/api/session', json={'session_id': session_id}).json()
    assert client.post('/api/session', json={'session_id': session_id}).json() == first
    assert client.post('/api/ingest', data={'session_id': session_id}).status_code == 400
    assert client.post('/api/ingest', data={'session_id': session_id}, files={'files': ('script.svg', b'<svg/>', 'image/svg+xml')}).status_code == 415
    assert client.post('/api/ingest', data={'session_id': session_id}, files={'files': ('empty.jpg', b'', 'image/jpeg')}).status_code == 413
    assert client.get(f'/api/session/{session_id}').json()['fragments'] == []
    assert client.get(f'/api/source/{uuid4()}').status_code == 404


def test_explicit_deletion_frees_voice_slot_and_preserves_other_sources(client):
    session_id = create(client)
    first = client.post('/api/ingest', data={'session_id': session_id}, files=[
        ('files', ('photo.jpg', b'photo', 'image/jpeg')),
        ('files', ('voice.wav', b'old voice', 'audio/wav')),
    ]).json()
    photo, voice = first['fragments']
    deleted = client.delete(f"/api/source/{voice['id']}")
    assert deleted.status_code == 200
    assert deleted.json()['fragments'] == [photo]
    assert client.get(voice['original_media_ref']).status_code == 404
    replacement = client.post('/api/ingest', data={'session_id': session_id}, files={'files': ('new.wav', b'new voice', 'audio/wav')}).json()
    assert replacement['fragments'][0] == photo
    assert replacement['fragments'][1]['id'] != voice['id']
    assert client.get(replacement['fragments'][1]['original_media_ref']).content == b'new voice'


def test_conversation_is_kept_and_woven_flag(client):
    session_id = create(client)
    turns = [{'role': 'weaver', 'text': 'Is that Shelly in photo 3?', 'question_id': 'who-1'},
             {'role': 'author', 'text': 'Yes, it’s Shelly.', 'question_id': 'who-1'}]
    session = client.post(f'/api/session/{session_id}/conversation', json=turns).json()
    assert [t['text'] for t in session['conversation']] == ['Is that Shelly in photo 3?', 'Yes, it’s Shelly.']
    assert all(t['at'] for t in session['conversation'])
    assert client.get(f'/api/session/{session_id}').json()['conversation'] == session['conversation']
    assert session['woven'] is False
