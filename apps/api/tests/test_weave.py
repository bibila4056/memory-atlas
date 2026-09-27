"""BundleWeaver-lite invariants (ADR 0008, EVALS E3) with deterministic providers — no network, no model."""
import io
import json

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.embeddings import FallbackProvider
from app.reasoning import HeuristicReasoning
from app.weave_models import AtomDraft, AtomizerOutput, RoleIntent, StoryIntent, VerifierReport
from app import weaver


def photo(color, when, noise=0, seed=0, size=(320, 240), box=(40, 120, 60, 200)):
    rng = np.random.default_rng(seed)
    arr = np.clip(np.ones((size[1], size[0], 3)) * color + rng.normal(0, 1, (size[1], size[0], 3)) * noise, 0, 255).astype(np.uint8)
    arr[box[0]:box[1], box[2]:box[3]] = (np.array(color) * 0.4).astype(np.uint8)  # each scene has its own composition
    img = Image.fromarray(arr)
    exif = Image.Exif()
    exif[0x8769] = {36867: when}
    buffer = io.BytesIO()
    img.save(buffer, 'JPEG', quality=92, exif=exif)
    return buffer.getvalue()


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('MEMORY_ATLAS_DATA_DIR', str(tmp_path))
    monkeypatch.setenv('MEMORY_ATLAS_REASONING', 'heuristic')
    monkeypatch.setenv('MEMORY_ATLAS_EMBEDDINGS', 'fallback')
    weaver.get_embedding_provider.cache_clear()
    with TestClient(app) as client:
        yield client
    weaver.get_embedding_provider.cache_clear()


def session_with(client, files, note=None):
    sid = client.post('/api/session', json={}).json()['session_id']
    data = {'session_id': sid, **({'text_json': json.dumps(note)} if note else {})}
    captured = client.post('/api/ingest', data=data, files=[('files', (name, raw, 'image/jpeg')) for name, raw in files]).json()
    return sid, {f['filename'] or 'note': f['id'] for f in captured['fragments']}


def test_weave_preserves_evidence_and_removes_burst_duplicate(client):
    street = photo((90, 110, 140), '2026:09:12 16:43:04')
    burst = photo((92, 111, 141), '2026:09:12 16:43:06')  # a near-identical second frame, different bytes
    shop = photo((200, 120, 60), '2026:09:12 16:36:42', noise=30, seed=2, box=(150, 230, 10, 120))
    food = photo((150, 80, 40), '2026:09:12 18:30:24', noise=10, seed=3, box=(0, 60, 220, 320))
    sid, ids = session_with(client, [('street.jpg', street), ('burst.jpg', burst), ('shop.jpg', shop), ('food.jpg', food)], note='Rain all day. Churros later.')
    response = client.post('/api/weave', json={'session_id': sid})
    assert response.status_code == 200
    result = response.json()
    assert result['providers'] == {'reasoning': 'heuristic', 'reasoning_model': None, 'embeddings': 'fallback', 'embedding_model': None, 'cross_modal': False}
    # the burst pair is one duplicate group, and only one of them can be in the story
    groups = [set(g['source_ids']) for g in result['duplicate_groups']]
    assert {ids['street.jpg'], ids['burst.jpg']} in groups
    selected_sources = {s for m in result['moments'] if m['id'] in result['selected']['moment_ids'] for s in m['image_source_ids']}
    assert result['selected']['score']['redundancy_penalty'] == 0
    # every source-derived object references only captured sources (E3)
    captured = set(ids.values())
    assert all(set(a['source_ids']) <= captured for a in result['atoms'])
    assert all(set(m['source_ids']) <= captured for m in result['moments'])
    assert selected_sources <= captured
    # every photo stayed eligible (none silently dropped)
    in_moments = {s for m in result['moments'] for s in m['image_source_ids']}
    assert {ids[n] for n in ['street.jpg', 'burst.jpg', 'shop.jpg', 'food.jpg']} <= in_moments
    assert 1 <= len(result['selected']['moment_ids']) <= 4
    assert len(result['seeds']) in (1, 2) and len(result['palette']) >= 3
    assert client.get(f'/api/weave/{sid}').json() == result
    assert client.get(f'/api/session/{sid}').json()['woven'] is True  # Capture will start a fresh page next time


def test_model_cannot_introduce_unknown_sources(client):
    sid, ids = session_with(client, [('a.jpg', photo((10, 200, 10), '2026:09:12 10:00:00'))])

    class Rogue(HeuristicReasoning):
        def atomize(self, evidence):
            return AtomizerOutput(atoms=[AtomDraft(source_ids=['00000000-0000-0000-0000-000000000000'], event='invented', salience=1),
                                         AtomDraft(source_ids=[evidence[0].id], event='real photo', salience=0.5)])
    result = weaver.weave(__import__('uuid').UUID(sid), reasoning=Rogue(), emb=FallbackProvider())
    assert [a.event for a in result.atoms] == ['real photo']


def test_verifier_gets_at_most_one_validated_replacement(client):
    colors = [(200, 40, 40), (40, 200, 40), (40, 40, 200), (200, 200, 40), (40, 200, 200)]
    boxes = [(0, 80, 0, 100), (160, 240, 220, 320), (0, 80, 220, 320), (160, 240, 0, 100), (80, 160, 110, 210)]
    files = [(f'p{i}.jpg', photo(c, f'2026:09:12 1{i}:00:00', noise=20, seed=i, box=boxes[i])) for i, c in enumerate(colors)]
    sid, _ = session_with(client, files)

    class Picky(HeuristicReasoning):
        def reframe(self, moments, instruction=None):
            return StoryIntent(intent='x', title='x', roles=[RoleIntent(role='Anchor', intent='a', query='photo'), RoleIntent(role='Detail', intent='d', query='photo'),
                                                             RoleIntent(role='Closing', intent='c', query='photo')])

        def verify(self, bundle, roles, alternates):
            return VerifierReport(coverage=3, coherence=3, complementarity=3, groundedness=5, visual_diversity=3, rationale='swap',
                                  weakest_moment_id=bundle[-1].id, replacement_moment_id='moment_999')  # not a supplied ID
    result = weaver.weave(__import__('uuid').UUID(sid), reasoning=Picky(), emb=FallbackProvider())
    assert result.replacement is None  # unknown replacement ID rejected by typed code
    assert result.selected.moment_ids == max(result.seeds, key=lambda b: b.score.total).moment_ids


def test_role_coverage_is_fit_weighted():
    pool = weaver.Pool(moments={}, embedding={}, text={}, dup_of={}, day_span=0, fit={('Anchor', 'm1'): 1.0, ('Anchor', 'm2'): 0.1})
    from app.weave_models import Moment
    from uuid import uuid4
    for m in ('m1', 'm2'):
        pool.moments[m] = Moment(id=m, title=m, atom_ids=['a'], source_ids=[uuid4()], summary='', salience=0.5)
        pool.embedding[m] = None
    good = weaver.score_bundle(['m1'], {'m1': 'Anchor'}, ['Anchor', 'Closing'], pool)
    weak = weaver.score_bundle(['m2'], {'m2': 'Anchor'}, ['Anchor', 'Closing'], pool)
    assert good.role_coverage == 0.5 and weak.role_coverage == 0.05


def test_weave_requires_a_photo(client):
    sid = client.post('/api/session', json={}).json()['session_id']
    client.post('/api/ingest', data={'session_id': sid, 'text_json': json.dumps('only words')})
    assert client.post('/api/weave', json={'session_id': sid}).status_code == 422


def test_live_reasoning_sends_schema_and_validates_output(client, monkeypatch):
    import httpx
    from app import reasoning
    sid, ids = session_with(client, [('a.jpg', photo((10, 200, 10), '2026:09:12 10:00:00'))], note='Coffee with Emily.')
    seen = {}

    def handler(request):
        body = json.loads(request.content)
        seen.update(model=body['model'], schema=body['response_format']['json_schema']['name'], auth=request.headers['authorization'],
                    has_image=any(part.get('type') == 'image_url' for part in body['messages'][1]['content']))
        atoms = {'atoms': [{'source_ids': [ids['a.jpg']], 'event': 'coffee with Emily', 'people': ['Emily'], 'salience': 0.9},
                           {'source_ids': ['not-a-real-id'], 'event': 'hallucinated', 'salience': 1}]}
        return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps(atoms)}}]})
    real_client = httpx.Client
    monkeypatch.setattr(reasoning.httpx, 'Client', lambda **kw: real_client(transport=httpx.MockTransport(handler)))
    monkeypatch.setenv('MEMORY_ATLAS_REASONING_MODEL', 'terra-test')
    monkeypatch.setenv('OPENAI_API_KEY', 'sk-test')
    live = reasoning.LiveReasoning()
    from app.evidence import extract
    from app import capture_store
    from uuid import UUID
    evidence = {str(f.id): extract(f, capture_store.get_source(f.id)[1]) for f in capture_store.get_session(UUID(sid)).fragments}
    atoms = weaver.build_atoms(live.atomize(list(evidence.values())), evidence)
    assert seen == {'model': 'terra-test', 'schema': 'AtomizerOutput', 'auth': 'Bearer sk-test', 'has_image': True}
    assert [a.event for a in atoms] == ['coffee with Emily']
