"""Structured reasoning provider (ADR 0010 / D-019): atomize, reframe, verify.

Modes, always recorded in the WeaveResult:
- live:      OpenAI-compatible /chat/completions with a JSON schema response (Terra by default,
             configured by MEMORY_ATLAS_REASONING_MODEL / _BASE_URL / _API_KEY).
- fixture:   offline-prepared structured output for a known set of source files, matched by the
             SHA-256 of the originals. Used for rehearsals without credentials; never presented as live.
- heuristic: no model at all; minimal atoms from metadata and the note itself.

Model outputs are validated with Pydantic and may reference only IDs supplied in the prompt.
"""
import base64
import io
import json
import os
import re
from pathlib import Path
from typing import Protocol

import httpx

from .evidence import Evidence
from .weave_models import AtomizerOutput, AtomDraft, Moment, ProviderMode, RoleIntent, StoryIntent, VerifierReport

FIXTURE_DIR = Path(__file__).parent / 'fixtures' / 'weave'


class ReasoningUnavailable(Exception):
    pass


class ReasoningProvider(Protocol):
    mode: ProviderMode
    model: str | None

    def atomize(self, evidence: list[Evidence]) -> AtomizerOutput: ...
    def reframe(self, moments: list[Moment], instruction: str | None = None) -> StoryIntent: ...
    def verify(self, bundle: list[Moment], roles: dict[str, str], alternates: list[Moment]) -> VerifierReport: ...


# ── prompts ───────────────────────────────────────────────────────────────
ATOMIZE = """You turn one person's fragments of a day into Memory Atoms.
Rules: one atom per fragment unless a note clearly describes several events (then one atom per event, same source_id).
Use only what is visible or written. Never invent names, places or times. People/places named in the note may be attached
to a photo atom only when the photo plausibly shows that moment. salience 0–1 = how central the fragment is to the day.
For each photo also set subject_kind ("object" when one clear subject stands apart from its background, e.g. food, a cup,
a single figure; "scene" for blended scenery, streets, interiors, views) and list up to 4 `details`: visible things worth
pointing at (a person, a dish, a sign) with a normalized [x0, y0, x1, y1] box. Label people as "person" unless the author
named them in an instruction attached to that photo.
Return JSON matching the schema. source_ids must be copied exactly from the fragment ids given."""

REFRAME = """Given the moments of one day, state the story intent and 3–4 flexible narrative roles.
The first role must be "Anchor". Other roles are chosen for THIS story (e.g. Human connection, Detail, Shift, Closing).
Each role has an intent and a short visual `query` (≤12 words) describing what a photo filling it would show.
Keywords: 3–6 short lowercase words from the evidence. Title: a short phrase from the author's own words when possible.
If an author_instruction is given, follow it for emphasis, role choice and tone, but never invent facts it implies."""

VERIFY = """You verify a whole Story Bundle, not items one by one. Score 1–5: coverage, coherence, complementarity,
groundedness (every claim traceable to evidence), visual_diversity. If one moment is clearly the weakest and one of the
supplied alternates would improve the bundle, name weakest_moment_id and replacement_moment_id (IDs from the lists only);
otherwise leave both null. Keep rationale under 60 words."""


def _image_part(ev: Evidence) -> dict:
    buffer = io.BytesIO()
    ev.image.save(buffer, 'JPEG', quality=80)
    return {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + base64.b64encode(buffer.getvalue()).decode()}}


def _moment_brief(m: Moment) -> dict:
    return {'id': m.id, 'title': m.title, 'summary': m.summary, 'people': m.people, 'place': m.place, 'moods': m.moods,
            'time': [t.isoformat() for t in m.time_range] if m.time_range else None, 'photos': len(m.image_source_ids)}


class LiveReasoning:
    mode: ProviderMode = 'live'

    def __init__(self):
        self.model = os.getenv('MEMORY_ATLAS_REASONING_MODEL')
        self.key = os.getenv('MEMORY_ATLAS_REASONING_API_KEY') or os.getenv('OPENAI_API_KEY')
        self.base = os.getenv('MEMORY_ATLAS_REASONING_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
        if not (self.model and self.key):
            raise ReasoningUnavailable('Set MEMORY_ATLAS_REASONING_MODEL and an API key to enable live reasoning.')

    def _call(self, system: str, content: list[dict], schema_model):
        body = {'model': self.model, 'temperature': 0.2, 'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': content}],
                'response_format': {'type': 'json_schema', 'json_schema': {'name': schema_model.__name__, 'schema': schema_model.model_json_schema(), 'strict': False}}}
        with httpx.Client(timeout=httpx.Timeout(90, connect=10)) as client:
            response = client.post(f'{self.base}/chat/completions', headers={'Authorization': f'Bearer {self.key}'}, json=body)
            response.raise_for_status()
        return schema_model.model_validate_json(response.json()['choices'][0]['message']['content'])

    def atomize(self, evidence):
        content: list[dict] = []
        for ev in evidence:
            meta = {'id': ev.id, 'modality': ev.fragment.modality, 'captured_at': ev.captured_at.isoformat() if ev.captured_at else None,
                    'author_instruction': ev.fragment.source_instruction}
            content.append({'type': 'text', 'text': json.dumps(meta) + (f"\nText: {ev.text}" if ev.text else '')})
            if ev.image is not None:
                content.append(_image_part(ev))
        return self._call(ATOMIZE, content, AtomizerOutput)

    def reframe(self, moments, instruction=None):
        payload = {'moments': [_moment_brief(m) for m in moments]}
        if instruction:  # author guidance: shapes emphasis and tone, never adds facts
            payload['author_instruction'] = instruction
        return self._call(REFRAME, [{'type': 'text', 'text': json.dumps(payload)}], StoryIntent)

    def verify(self, bundle, roles, alternates):
        payload = {'bundle': [{**_moment_brief(m), 'role': roles.get(m.id)} for m in bundle], 'alternates': [_moment_brief(m) for m in alternates]}
        return self._call(VERIFY, [{'type': 'text', 'text': json.dumps(payload)}], VerifierReport)


class FixtureReasoning:
    """Offline-prepared outputs keyed by original-file hashes. See fixtures/weave/*.json → `prepared_by`."""
    mode: ProviderMode = 'fixture'

    def __init__(self, fixture: dict, by_hash: dict[str, str]):
        self.fixture, self.by_hash, self.model = fixture, by_hash, fixture.get('prepared_by')

    @classmethod
    def match(cls, evidence: list[Evidence]) -> 'FixtureReasoning | None':
        hashes = {ev.sha256: ev.id for ev in evidence if ev.fragment.modality != 'audio'}
        for path in sorted(FIXTURE_DIR.glob('*.json')):
            fixture = json.loads(path.read_text())
            needed = {h for atom in fixture['atoms'] if not atom.get('optional') for h in atom['source_sha256']}
            if needed & hashes.keys():  # per-file: atoms apply only to originals that are present
                return cls(fixture, hashes)
        return None

    def atomize(self, evidence):
        atoms = [AtomDraft(source_ids=[self.by_hash[h] for h in a['source_sha256']], **{k: v for k, v in a.items() if k not in ('source_sha256', 'optional')})
                 for a in self.fixture['atoms'] if all(h in self.by_hash for h in a['source_sha256'])]
        return AtomizerOutput(atoms=atoms)

    def reframe(self, moments, instruction=None):
        return StoryIntent.model_validate(self.fixture['story'])

    def verify(self, bundle, roles, alternates):
        return VerifierReport.model_validate(self.fixture['verifier'])


class HeuristicReasoning:
    mode: ProviderMode = 'heuristic'
    model = None

    def atomize(self, evidence):
        atoms = []
        for ev in evidence:
            if ev.fragment.modality == 'image':
                when = ev.captured_at.strftime('%-I:%M %p').lower() if ev.captured_at else 'an undated moment'
                atoms.append(AtomDraft(source_ids=[ev.id], event=f'photo at {when}', salience=0.5))
            elif ev.text:
                from .art_director import likely_names
                names = likely_names([ev.text])
                atoms.append(AtomDraft(source_ids=[ev.id], event=ev.text.split('.')[0][:120] or 'note', people=names, salience=0.6))
        return AtomizerOutput(atoms=atoms)

    def reframe(self, moments, instruction=None):
        return StoryIntent(intent='A day told through its most distinct moments.', title=moments[0].title if moments else 'A day',
            roles=[RoleIntent(role='Anchor', intent='The moment the day is about', query='the most memorable scene of the day'),
                   RoleIntent(role='Detail', intent='A close, specific detail', query='a close-up of a small object'),
                   RoleIntent(role='Closing', intent='How the day ended', query='the end of the day, food or evening light')])

    def verify(self, bundle, roles, alternates):
        return VerifierReport(coverage=3, coherence=3, complementarity=3, groundedness=5, visual_diversity=3, rationale='Heuristic check only: no model verification ran.')


def get_reasoning_provider(evidence: list[Evidence]) -> ReasoningProvider:
    preference = os.getenv('MEMORY_ATLAS_REASONING', 'auto')  # auto | live | fixture | heuristic
    if preference in ('auto', 'live'):
        try:
            return LiveReasoning()
        except ReasoningUnavailable:
            if preference == 'live':
                raise
    if preference in ('auto', 'fixture'):
        fixture = FixtureReasoning.match(evidence)
        if fixture:
            return fixture
    return HeuristicReasoning()
