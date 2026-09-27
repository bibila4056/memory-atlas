"""docs/ART_DIRECTION.md rules: tool choice, placement, arrows, ≤2 questions, router modes, hand-cut stickers."""
import io
from uuid import uuid4

import numpy as np
from PIL import Image

from app import art_director as ad
from app import art_tools
from app.cutout import hand_cut
from app.weave_models import Detail, MemoryAtom


def atom(sid, event, kind=None, details=(), people=(), objects=(), place=None):
    return MemoryAtom(id=f'a-{event}', source_ids=[sid], event=event, subject_kind=kind, details=list(details),
                      people=list(people), objects=list(objects), place=place, salience=0.5)


def test_mentions_are_plural_and_case_insensitive():
    assert ad.mentioned('churro', 'the Churros at Morcilla')
    assert ad.mentioned('flan', 'flan and churros')
    assert not ad.mentioned('flan', 'flannel shirt')


def test_questions_only_for_what_photos_cannot_show():
    walk, food = uuid4(), uuid4()
    atoms = [atom(walk, 'walk', 'object', [Detail(label='person', box=(0.4, 0.4, 0.6, 0.9))]),
             atom(food, 'churros', 'object', [Detail(label='churros', box=(0.1, 0.3, 0.5, 0.8)), Detail(label='flan', box=(0.4, 0.6, 0.9, 0.9))])]
    context = atoms + [atom(uuid4(), 'note', place='Morcilla')]
    names = {str(walk): 'photo 1', str(food): 'photo 2'}
    words = {'note': 'A film shop with Shelly, then flan and churros at Morcilla.'}
    qs = ad.questions(atoms, words, names, {}, context)
    # flan/churros match exactly one photo → linked silently; the unnamed person gets one question with the likely name
    assert [q.text for q in qs] == ['Is that Shelly in photo 1?'] and qs[0].suggestions == ['Shelly']
    # once the author answered, nothing more is asked
    assert ad.questions(atoms, words, names, {str(walk): 'This is Shelly'}, context) == []


def test_router_prompts_come_from_the_vendored_skills():
    tape = art_tools.tape_prompt('churros in a glass')
    assert 'genuine transparent RGBA' in tape and 'churros in a glass' in tape
    doodle = art_tools.doodle_prompt('the umbrella and the walking figure')
    assert 'unfinished private travel-notebook draft' in doodle and 'the umbrella and the walking figure' in doodle
    assert 'half of the final image is the real photograph' in art_tools.scene_prompt('rain on a window')


def photo_bytes():
    img = Image.new('RGB', (400, 600), (240, 236, 228))
    img.paste((150, 80, 40), (120, 150, 280, 450))
    b = io.BytesIO(); img.save(b, 'JPEG'); return b.getvalue()


def test_router_modes_live_then_cache_then_unavailable(tmp_path, monkeypatch):
    monkeypatch.setenv('MEMORY_ATLAS_DATA_DIR', str(tmp_path))
    request = ad.ArtRequest(source_id='s1', moment_id='m1', tool='tape_collage', treatment='DISTILL', reason='test', placement='beside_original')
    calls = []

    class Fake:
        def generate(self, source_png, prompt, refs, transparent, size):
            calls.append((transparent, size, len(refs)))
            motif = Image.new('RGBA', (512, 768), (0, 0, 0, 0))
            motif.paste((200, 120, 60, 255), (150, 200, 360, 560))
            b = io.BytesIO(); motif.save(b, 'PNG'); return b.getvalue()
    live = art_tools.resolve(request, photo_bytes(), 'a cup', adapter_factory=Fake)
    assert live.generation_mode == 'live' and calls == [(True, '1024x1536', 0)]
    sticker = Image.open(tmp_path / 'art' / live.asset_ref.split('/')[-1])
    alpha = np.asarray(sticker)[..., 3]
    assert alpha.min() == 0 and alpha.max() == 255  # cut out, with a paper margin around the motif

    def unavailable():
        raise art_tools.ImageModelUnavailable('no key')
    cached = art_tools.resolve(request, photo_bytes(), 'a cup', adapter_factory=unavailable)
    assert cached.generation_mode == 'cache' and cached.asset_ref == live.asset_ref
    other = request.model_copy(update={'tool': 'doodle'})
    assert art_tools.resolve(other, photo_bytes(), 'a cup', adapter_factory=unavailable).generation_mode == 'unavailable'


def test_hand_cut_on_paper_background():
    page = Image.new('RGB', (600, 800), (246, 243, 238))
    page.paste((120, 60, 30), (200, 250, 400, 600))
    cut = hand_cut(page)
    alpha = np.asarray(cut)[..., 3]
    assert cut.size[0] < 600 and alpha[alpha.shape[0] // 2, alpha.shape[1] // 2] == 255 and alpha[0, 0] == 0


def test_names_are_not_sentence_openers():
    notes = ["Shelly and I found a tiny film shop.", "Shelly insisted we split the flan.", "Okay, I'm completely soaked, but this is the best churro."]
    assert ad.likely_names(notes) == ['Shelly']
    assert ad.likely_names(["A walk with Emily in the rain."]) == ['Emily']


def test_demo_tools_tape_the_food_and_extend_the_most_blended_scene(monkeypatch):
    """Author's demo: churros → tape collage, restaurant window → gathered scenes. People are never redrawn; doodle is off."""
    from types import SimpleNamespace as NS
    monkeypatch.delenv('MEMORY_ATLAS_ART_TOOLS', raising=False)
    walk, shop, food, window = (uuid4() for _ in range(4))
    atoms = [atom(walk, 'walk', 'object', [Detail(label='person', box=(0.4, 0.4, 0.6, 0.9))], objects=['umbrella']),
             atom(shop, 'shop', 'scene', [Detail(label='shop sign', box=(0.1, 0.1, 0.3, 0.2))]),
             atom(food, 'churros', 'object', [Detail(label='churros', box=(0.1, 0.3, 0.5, 0.8))]),
             atom(window, 'window', 'scene')]
    moments = [NS(id=f'm{i}', image_source_ids=[a.source_ids[0]], atom_ids=[a.id]) for i, a in enumerate(atoms)]
    result = NS(atoms=atoms, moments=moments, selected=NS(moment_ids=[m.id for m in moments], roles={'m0': 'Anchor'}))
    picks = ad.choose_tools(result, {})
    assert [(r.tool, r.source_id) for r in picks] == [('tape_collage', str(food)), ('scene_extension', str(window))]
    assert all(r.tool != 'doodle' for r in picks)
