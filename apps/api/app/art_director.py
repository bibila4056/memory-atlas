"""Art Director rules (docs/ART_DIRECTION.md) — deterministic, typed, testable.

Given a finished WeaveResult it decides:
  • which selected photos get an art treatment, and with which tool (tape_collage / scene_extension; doodle when enabled);
  • photos showing a person are never redrawn;
  • where each cut-out goes (always beside its own original);
  • which arrows to draw (only when the author's words mention something visibly present);
and, before weaving, which ≤2 follow-up questions are worth asking the author.
"""
import os
import re
from typing import Literal

import numpy as np
from PIL import Image
from pydantic import Field

from .models import ContractModel
from .weave_models import Detail, MemoryAtom, WeaveResult

Tool = Literal['tape_collage', 'doodle', 'scene_extension']
TREATMENT = {'tape_collage': 'DISTILL', 'doodle': 'DISTILL', 'scene_extension': 'EXTEND'}
MAX_ART, MAX_ARROWS, MAX_QUESTIONS = 2, 2, 2  # questions: the route trims to MEMORY_ATLAS_MAX_QUESTIONS (demo: 1)
LINE_LED = {'person', 'people', 'building', 'street', 'bike', 'bicycle', 'tree', 'plant', 'flower', 'house', 'bridge', 'dog', 'cat'}


class ArtRequest(ContractModel):
    source_id: str
    moment_id: str
    tool: Tool
    treatment: Literal['DISTILL', 'EXTEND']
    reason: str
    placement: Literal['beside_original', 'replaces_print_zone'] = Field(description='Cut-outs sit beside their original; scene extensions take the print zone and keep the photo inside them.')


class Annotation(ContractModel):
    text: str = Field(description="The author's exact words.")
    source_ids: list[str] = Field(min_length=2, description='[photo, words] — evidence on both sides.')
    target_source_id: str
    box: tuple[float, float, float, float]


class Question(ContractModel):
    id: str
    source_id: str = Field(description='Photo the question is about; the answer is stored as its source_instruction.')
    text: str
    suggestions: list[str] = []


class ArtDirection(ContractModel):
    requests: list[ArtRequest]
    annotations: list[Annotation]


def singular(word: str) -> str:
    return re.sub(r'(ies)$', 'y', re.sub(r'(?<=[^s])s$', '', word.lower()))


def mentioned(phrase: str, text: str) -> bool:
    words = [singular(w) for w in re.findall(r"[a-zA-Z']+", text)]
    target = [singular(w) for w in phrase.split()]
    return any(words[i:i + len(target)] == target for i in range(len(words) - len(target) + 1))


def subject_kind(atom: MemoryAtom, image: Image.Image | None) -> Literal['object', 'scene']:
    """Model label when present; otherwise a center-surround saliency estimate (clear subject ⇒ center differs from border)."""
    if atom.subject_kind:
        return atom.subject_kind
    if image is None:
        return 'scene'
    a = np.asarray(image.convert('RGB').resize((96, 96)), dtype=float)
    center, border = a[24:72, 24:72].reshape(-1, 3), np.concatenate([a[:12].reshape(-1, 3), a[-12:].reshape(-1, 3), a[:, :12].reshape(-1, 3), a[:, -12:].reshape(-1, 3)])
    contrast = np.linalg.norm(center.mean(0) - border.mean(0)) / (border.std(0).mean() + 1e-6)
    return 'object' if contrast > 1.2 else 'scene'


def enabled_tools() -> set[str]:
    """Which art skills this install runs (MEMORY_ATLAS_ART_TOOLS). Demo default: tape collage + gathered-scenes style
    extension; doodle stays vendored but off until it is demonstrated."""
    raw = os.getenv('MEMORY_ATLAS_ART_TOOLS', 'tape_collage,scene_extension')
    return {t.strip() for t in raw.split(',') if t.strip() in TREATMENT}


def _has_person(atom: MemoryAtom) -> bool:
    return bool(atom.people) or any(d.label.lower() in ('person', 'people') for d in atom.details)


def choose_tools(result: WeaveResult, images: dict[str, Image.Image]) -> list[ArtRequest]:
    atoms = {a.id: a for a in result.atoms}
    tools = enabled_tools()
    objects: list[ArtRequest] = []
    scenes: list[tuple[int, ArtRequest]] = []
    for moment_id in result.selected.moment_ids:
        moment = next(m for m in result.moments if m.id == moment_id)
        if not moment.image_source_ids:
            continue
        photo = str(moment.image_source_ids[0])
        atom = next((atoms[a] for a in moment.atom_ids if str(atoms[a].source_ids[0]) == photo), atoms[moment.atom_ids[0]])
        if _has_person(atom):  # identity-bearing photos stay PRESERVE: never redraw a real person
            continue
        kind = subject_kind(atom, images.get(photo))
        if kind == 'scene':
            # The Anchor's own print is never replaced (rule B5).
            if result.selected.roles.get(moment_id) == 'Anchor' or 'scene_extension' not in tools:
                continue
            scenes.append((len(atom.details), ArtRequest(source_id=photo, moment_id=moment_id, tool='scene_extension', treatment='EXTEND',
                           reason='blended scenery, nothing to point at → gathered scenes (half photo, half drawing)', placement='replaces_print_zone')))
        else:
            labels = {d.label.lower() for d in atom.details} | {o.lower() for o in atom.objects}
            line_led = bool(labels & LINE_LED)
            tool = 'doodle' if line_led and 'doodle' in tools else 'tape_collage' if 'tape_collage' in tools else None
            if tool is None or any(r.tool == tool for r in objects):  # variety: at most one of each
                continue
            objects.append(ArtRequest(source_id=photo, moment_id=moment_id, tool=tool, treatment='DISTILL', placement='beside_original',
                                      reason=f"clear subject ({', '.join(sorted(labels)[:3]) or 'object'}) → {'line-led, doodle' if tool == 'doodle' else 'color blocks, tape collage'}"))
    # The most blended scene (fewest things worth pointing at) gains the most from being extended.
    picked = objects[:1] + [min(scenes, key=lambda s: s[0])[1]] if scenes else objects[:1]
    picked += [r for r in objects[1:]][:MAX_ART - len(picked)]
    order = {m: i for i, m in enumerate(result.selected.moment_ids)}
    return sorted(picked[:MAX_ART], key=lambda r: order[r.moment_id])


def annotate(result: WeaveResult, words: dict[str, str]) -> list[Annotation]:
    """Arrow only when the author's text names something with a detected region in a selected photo."""
    out: list[Annotation] = []
    selected_photos = {str(s) for m in result.moments if m.id in result.selected.moment_ids for s in m.image_source_ids[:1]}
    for atom in result.atoms:
        photo = str(atom.source_ids[0])
        if photo not in selected_photos:
            continue
        for detail in atom.details:
            names = atom.people if detail.label.lower() in ('person', 'people') and len(atom.people) == 1 else [detail.label]
            for word_source, text in words.items():
                hit = next((n for n in names if mentioned(n, text)), None)
                if hit and len(out) < MAX_ARROWS and all(a.text.lower() != hit.lower() for a in out):
                    exact = re.search(re.escape(hit.rstrip('s')) + r'\w*', text, re.I)
                    out.append(Annotation(text=exact.group(0) if exact else hit, source_ids=[photo, word_source], target_source_id=photo, box=detail.box))
    return out


def direct(result: WeaveResult, images: dict[str, Image.Image], words: dict[str, str]) -> ArtDirection:
    return ArtDirection(requests=choose_tools(result, images), annotations=annotate(result, words))


STARTERS = {'It', 'I', 'The', 'We', 'My', 'This', 'That', 'But', 'And', 'Okay', 'Ok', 'So', 'Then', 'Oh', 'Well', 'Yes', 'No', 'Just', 'Today', 'Also', 'After', 'Before', 'When', 'Luckily'}


def likely_names(texts: list[str]) -> list[str]:
    """Capitalised words that behave like names: seen mid-sentence, or capitalised more than once.
    A word that only ever opens a sentence ("Okay, I'm soaked…") is not a name."""
    mid, starts = set(), {}
    for text in texts:
        for sentence in re.split(r'(?<=[.!?])\s+|\n+', text):
            tokens = re.findall(r"[A-Za-z][a-z']*", sentence)
            for i, token in enumerate(tokens):
                if token[0].isupper() and len(token) > 1 and "'" not in token and token not in STARTERS:
                    if i:
                        mid.add(token)
                    else:
                        starts[token] = starts.get(token, 0) + 1
    return sorted(mid | {w for w, n in starts.items() if n > 1})


def questions(atoms: list[MemoryAtom], words: dict[str, str], names: dict[str, str], instructions: dict[str, str | None],
              context_atoms: list[MemoryAtom] | None = None) -> list[Question]:
    """≤2 short questions, only for facts the photos can't show. Silent when evidence already agrees.
    `atoms` are photo atoms; `context_atoms` (all atoms, incl. the note's) tell places apart from people."""
    context_atoms = context_atoms or atoms
    text = ' '.join(words.values())
    people_named = likely_names(list(words.values()))
    photos_with_person = [a for a in atoms if any(d.label.lower() in ('person', 'people') for d in a.details) and not a.people
                          and not instructions.get(str(a.source_ids[0]))]
    out: list[Question] = []
    # Who is this? Only when the note names people and a photo shows an unnamed person.
    known_places = ' '.join(a.place or '' for a in context_atoms) + ' ' + ' '.join(o for a in context_atoms for o in a.objects)
    model_people = list(dict.fromkeys(p for a in context_atoms for p in a.people))       # people the model found in the words
    people_in_text = model_people or [p for p in people_named if not mentioned(p.lower(), known_places.lower())]
    for atom in photos_with_person[:1]:
        sid = str(atom.source_ids[0])
        # One candidate → that's the guess. Several → the one the author mentions most, if it clearly leads.
        counts = sorted(((len(re.findall(rf'\b{re.escape(p)}\b', text)), p) for p in people_in_text), reverse=True)
        guess = counts[0][1] if counts and (len(counts) == 1 or counts[0][0] > counts[1][0]) else None
        out.append(Question(id=f'who-{sid[:8]}', source_id=sid, suggestions=[guess] if guess else [],
                            text=f"Is that {guess} in {names[sid]}?" if guess else f"Who is in {names[sid]}?"))
    # Which photo? Only when the note names a thing seen in more than one photo (a unique match links silently).
    for thing in sorted({d.label for a in atoms for d in a.details} - {'person', 'people'}):
        seen = [a for a in atoms if any(d.label == thing for d in a.details)]
        if mentioned(thing, text) and len(seen) > 1 and len(out) < MAX_QUESTIONS:
            out.append(Question(id=f'which-{thing}', source_id=str(seen[0].source_ids[0]), text=f"Which photo shows the {thing} you mentioned?",
                                suggestions=[names[str(a.source_ids[0])] for a in seen]))
    return out[:MAX_QUESTIONS]
