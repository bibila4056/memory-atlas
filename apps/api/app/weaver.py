"""BundleWeaver-lite — a small-scale adaptation of BundleWeaver.

Rong Shan et al., "Weaving Visual Narratives: Agentic Image Bundle Composition Beyond Atomic
Visual Matching", arXiv:2608.28695 (EMNLP 2026); code: github.com/LaVieEnRose365/Image-Bundle-Composition.

Recognizable mechanisms implemented here (see RESEARCH.md R1, ADR 0008):
  1. story reframing → story intent + flexible narrative roles         (reasoning provider)
  2. role-conditioned candidate retrieval, top-3 per role             (SigLIP 2 text→image, or lexical fallback)
  3. two diverse seeds: best Anchor + strongest non-redundant alternative
  4. adaptive expansion: add the candidate that best fills a *missing role*, by marginal bundle gain
  5. whole-bundle verification, at most one replacement                (reasoning provider, IDs validated here)
Deliberate simplifications: one short session (≈10 fragments), no beam search, no spatiotemporal pruning,
no IBCBench-scale evaluation. Weights are the documented MVP heuristics (ARCHITECTURE.md §2.D).
"""
import itertools
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

import numpy as np

from . import capture_store as store
from .embeddings import EmbeddingProvider, get_embedding_provider
from .evidence import Evidence, extract, hamming, palette
from .reasoning import ReasoningProvider, get_reasoning_provider
from .weave_models import (BundleScore, DuplicateGroup, MemoryAtom, Moment, ProviderInfo, RoleCandidates, ScoredBundle,
                           StageTiming, StoryIntent, VerifierReport, WeaveResult)

WEIGHTS = {'role_coverage': 0.30, 'salience': 0.20, 'visual_diversity': 0.15, 'emotional_coverage': 0.15, 'temporal_coverage': 0.10, 'grounding': 0.10}
REDUNDANCY_PENALTY = 0.25
MAX_BUNDLE, MIN_BUNDLE, TOP_K = 4, 3, 3
DHASH_NEAR, EMBED_NEAR = 8, {'siglip2': 0.95, 'fallback': 0.985}
STOP = {'a', 'an', 'the', 'of', 'to', 'in', 'on', 'at', 'with', 'and', 'or', 'for', 'is', 'was', 'this', 'that', 'my', 'we', 'us', 'i', 'it', 'photo'}


def tokens(text: str) -> set[str]:
    return {t for t in re.findall(r'[a-z]+', text.lower()) if t not in STOP and len(t) > 2}


@dataclass
class Pool:
    """Everything the weaver may choose from; model outputs are checked against it."""
    moments: dict[str, Moment]
    embedding: dict[str, np.ndarray | None]  # moment_id → visual embedding
    text: dict[str, str]
    dup_of: dict[str, str]                    # source_id → duplicate group id
    day_span: float                           # seconds between first and last reliable timestamp
    main_day: object = None                   # date most photos were taken on
    fit: dict = None                          # (role, moment_id) → retrieval relevance in [0, 1]


# ── 1. atoms ───────────────────────────────────────────────────────────────
def build_atoms(drafts, evidence: dict[str, Evidence]) -> list[MemoryAtom]:
    atoms = []
    for i, draft in enumerate(drafts.atoms):
        ids = [sid for sid in draft.source_ids if sid in evidence]
        told = [evidence[sid].fragment.source_instruction for sid in ids if evidence[sid].fragment.source_instruction]
        if told:  # the author's own answer ("This is Shelly") is evidence, not inference
            draft = draft.model_copy(update={'people': sorted(set(draft.people) | {w for t in told for w in re.findall(r'\b[A-Z][a-z]+\b', t) if w not in ('This', 'That', 'The', 'It', 'Is', 'My', 'We', 'I')})})
        if not ids:  # the model referenced an ID we never supplied → drop, never invent evidence
            continue
        times = [evidence[sid].captured_at for sid in ids if evidence[sid].captured_at]
        texts = [evidence[sid].text for sid in ids if evidence[sid].text]
        atoms.append(MemoryAtom(id=f'atom_{i + 1}', source_ids=[UUID(sid) for sid in ids], event=draft.event.strip(), people=draft.people,
            place=draft.place, objects=draft.objects, moods=draft.moods, themes=draft.themes, salience=draft.salience,
            captured_at=min(times) if times else None, verbatim_text=texts[0] if texts else None,
            must_preserve=all(evidence[sid].fragment.keep_original for sid in ids),
            subject_kind=draft.subject_kind, details=draft.details if any(evidence[sid].image is not None for sid in ids) else []))
    return atoms


# ── 2. duplicates ──────────────────────────────────────────────────────────
def find_duplicates(images: list[Evidence], vectors: dict[str, np.ndarray], provider: str, salience: dict[str, float]) -> list[DuplicateGroup]:
    parent = {ev.id: ev.id for ev in images}
    reason: dict[tuple[str, str], str] = {}

    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in itertools.combinations(images, 2):
        why = 'exact' if a.sha256 == b.sha256 else 'perceptual' if hamming(a.dhash, b.dhash) <= DHASH_NEAR else \
            'embedding' if float(vectors[a.id] @ vectors[b.id]) >= EMBED_NEAR[provider] else None
        if why:
            reason[(a.id, b.id)] = why
            parent[root(a.id)] = root(b.id)
    groups: dict[str, list[str]] = {}
    for ev in images:
        groups.setdefault(root(ev.id), []).append(ev.id)
    out = []
    for n, members in enumerate(m for m in groups.values() if len(m) > 1):
        kinds = {reason[p] for p in reason if p[0] in members and p[1] in members}
        kept = max(members, key=lambda sid: (salience.get(sid, 0), -members.index(sid)))
        out.append(DuplicateGroup(id=f'dup_{n + 1}', source_ids=[UUID(m) for m in members], kept_source_id=UUID(kept),
                                  reason='exact' if kinds == {'exact'} else 'perceptual' if 'perceptual' in kinds else 'embedding'))
    return out


# ── 3. moments ─────────────────────────────────────────────────────────────
def group_moments(atoms: list[MemoryAtom], evidence: dict[str, Evidence], vectors: dict[str, np.ndarray]) -> list[Moment]:
    """Same event label → same moment; otherwise photos ≤10 min apart that look alike merge.
    Notes/voice attach to the moment they mention (event label or shared people/place/objects)."""
    def key(atom):
        return ' '.join(sorted(tokens(atom.event)))
    image_atoms = sorted([a for a in atoms if evidence[str(a.source_ids[0])].fragment.modality == 'image'],
                         key=lambda a: a.captured_at or datetime.max)
    clusters: list[list[MemoryAtom]] = []
    for atom in image_atoms:
        home = next((c for c in clusters if key(c[0]) == key(atom)), None)
        if home is None and clusters and atom.captured_at and clusters[-1][-1].captured_at:
            last = clusters[-1][-1]
            gap = abs((atom.captured_at - last.captured_at).total_seconds())
            sim = float(vectors[str(atom.source_ids[0])] @ vectors[str(last.source_ids[0])])
            home = clusters[-1] if gap <= 600 and sim >= 0.8 else None
        (home.append(atom) if home is not None else clusters.append([atom]))
    for atom in [a for a in atoms if a not in image_atoms]:
        words = tokens(' '.join([atom.event, *atom.people, atom.place or '', *atom.objects]))
        best = max(clusters, default=None, key=lambda c: (key(c[0]) == key(atom), len(words & tokens(' '.join(
            [x.event for x in c] + [p for x in c for p in x.people] + [x.place or '' for x in c] + [o for x in c for o in x.objects])))))
        overlap = best is not None and (key(best[0]) == key(atom) or words & tokens(' '.join([x.event for x in best] + [p for x in best for p in x.people] + [x.place or '' for x in best] + [o for x in best for o in x.objects])))
        (best.append(atom) if overlap else clusters.append([atom]))
    moments = []
    for n, cluster in enumerate(clusters):
        lead = max(cluster, key=lambda a: a.salience)
        times = sorted(a.captured_at for a in cluster if a.captured_at)
        sources = list(dict.fromkeys(s for a in cluster for s in a.source_ids))
        moments.append(Moment(id=f'moment_{n + 1}', title=lead.event[:1].upper() + lead.event[1:], atom_ids=[a.id for a in cluster],
            source_ids=sources, image_source_ids=[s for s in sources if evidence[str(s)].fragment.modality == 'image'],
            summary='; '.join(dict.fromkeys(a.event for a in cluster)), people=sorted({p for a in cluster for p in a.people}),
            place=next((a.place for a in cluster if a.place), None), moods=sorted({m for a in cluster for m in a.moods}),
            salience=max(a.salience for a in cluster), time_range=(times[0], times[-1]) if times else None))
    return moments


# ── 4. bundle scoring ──────────────────────────────────────────────────────
def score_bundle(ids: list[str], roles: dict[str, str], role_names: list[str], pool: Pool) -> BundleScore:
    ms = [pool.moments[i] for i in ids]
    vecs = [pool.embedding[i] for i in ids if pool.embedding[i] is not None]
    pairs = list(itertools.combinations(range(len(vecs)), 2))
    diversity = 1 - float(np.mean([vecs[a] @ vecs[b] for a, b in pairs])) if pairs else 0.5
    all_moods = {m for x in pool.moments.values() for m in x.moods}
    times = [t for m in ms if m.time_range for t in m.time_range if pool.main_day is None or t.date() == pool.main_day]
    temporal = ((max(times) - min(times)).total_seconds() / pool.day_span) if len(times) >= 2 and pool.day_span else 0.5
    groups = [{pool.dup_of.get(str(s)) for s in m.image_source_ids} - {None} for m in ms]
    redundant = len(ids) - len(set(ids)) + sum(1 for a, b in itertools.combinations(range(len(ms)), 2) if groups[a] & groups[b])
    redundant += sum(1 for a, b in pairs if float(vecs[a] @ vecs[b]) >= 0.92)
    parts = {
        # narrative-role coverage is fit-weighted: a moment only covers a role as well as it matches that role's intent
        'role_coverage': sum(max((pool.fit.get((roles[i], i), 0.0) for i in ids if roles.get(i) == r), default=0.0) for r in role_names) / len(role_names),
        'salience': float(np.mean([m.salience for m in ms])) if ms else 0,
        'visual_diversity': float(np.clip(diversity * 2, 0, 1)),  # cosine distances between real photos rarely exceed 0.5
        'emotional_coverage': len({x for m in ms for x in m.moods}) / len(all_moods) if all_moods else 0.5,
        'temporal_coverage': float(np.clip(temporal, 0, 1)),
        'grounding': float(np.mean([1.0 if m.image_source_ids else 0.5 for m in ms])) if ms else 0,
    }
    penalty = REDUNDANCY_PENALTY * redundant
    return BundleScore(total=round(sum(WEIGHTS[k] * v for k, v in parts.items()) - penalty, 4), redundancy_penalty=round(penalty, 4),
                       **{k: round(v, 4) for k, v in parts.items()})


# ── 5. role retrieval + BundleWeaver-lite ──────────────────────────────────
def retrieve(story: StoryIntent, pool: Pool, emb: EmbeddingProvider) -> list[RoleCandidates]:
    ids = list(pool.moments)
    lexical = np.array([[len(tokens(r.query + ' ' + r.intent) & tokens(pool.text[i])) / max(1, len(tokens(r.query + ' ' + r.intent)))
                         for i in ids] for r in story.roles])
    if emb.cross_modal:
        # SigLIP 2 text→image: role query vs each moment's photos; text-only moments keep their lexical score.
        queries = emb.embed_texts([f'a photo of {r.query}' for r in story.roles])
        visual = np.array([[float(q @ pool.embedding[i]) if pool.embedding[i] is not None else np.nan for i in ids] for q in queries])
        lo, hi = np.nanmin(visual, axis=1, keepdims=True), np.nanmax(visual, axis=1, keepdims=True)
        visual = (visual - lo) / np.maximum(hi - lo, 1e-6)
        sims = np.where(np.isnan(visual), lexical, 0.75 * visual + 0.25 * lexical)
    else:
        sims = lexical
    out = []
    pool.fit = {(r.role, i): float(s) for r, row in zip(story.roles, sims) for s, i in zip(row, ids)}
    for r, row in zip(story.roles, sims):
        scored = sorted(((0.8 * float(s) + 0.2 * pool.moments[i].salience, i) for s, i in zip(row, ids)
                         if r is not story.roles[0] or pool.moments[i].image_source_ids), reverse=True)[:TOP_K]
        out.append(RoleCandidates(role=r.role, intent=r.intent, query=r.query, candidate_moment_ids=[i for _, i in scored], scores=[round(s, 4) for s, _ in scored]))
    return out


def redundant_with(a: str, b: str, pool: Pool) -> bool:
    ga = {pool.dup_of.get(str(s)) for s in pool.moments[a].image_source_ids} - {None}
    gb = {pool.dup_of.get(str(s)) for s in pool.moments[b].image_source_ids} - {None}
    return a == b or bool(ga & gb)


def expand(seed: str, seed_name, candidates: list[RoleCandidates], pool: Pool) -> ScoredBundle:
    role_names = [c.role for c in candidates]
    ids, roles = [seed], {seed: role_names[0]}
    log = [f'seed {seed} as {role_names[0]}']
    while len(ids) < MAX_BUNDLE:
        base = score_bundle(ids, roles, role_names, pool).total
        options = [(score_bundle(ids + [m], {**roles, m: c.role}, role_names, pool).total - base, c.role, m)
                   for c in candidates if c.role not in roles.values()
                   for m in c.candidate_moment_ids if all(not redundant_with(m, x, pool) for x in ids)]
        if not options:
            break
        gain, role, moment = max(options)
        if gain <= 0 and len(ids) >= MIN_BUNDLE:
            break
        if gain <= 0 and len(ids) < MIN_BUNDLE and gain < -0.1:
            break
        ids.append(moment)
        roles[moment] = role
        log.append(f'+{moment} fills missing role {role} (gain {gain:+.3f})')
    return ScoredBundle(seed=seed_name, moment_ids=ids, roles=roles, score=score_bundle(ids, roles, role_names, pool), expansion_log=log)


def seeds(candidates: list[RoleCandidates], pool: Pool) -> list[tuple[str, str]]:
    # Invariant: the Anchor is a visual moment (DESIGN.md §7 "one clear visual anchor").
    visual = lambda m: bool(pool.moments[m].image_source_ids)
    anchor = [m for m in candidates[0].candidate_moment_ids if visual(m)] or [m for m in pool.moments if visual(m)]
    first = anchor[0]
    alternatives = [m for m in anchor[1:] + [m for c in candidates[1:] for m in c.candidate_moment_ids] if visual(m) and not redundant_with(m, first, pool)]
    return [(first, 'anchor')] + ([(alternatives[0], 'alternative')] if alternatives else [])


def verify_and_replace(best: ScoredBundle, verifier: VerifierReport, candidates: list[RoleCandidates], pool: Pool) -> tuple[ScoredBundle, str | None]:
    """At most one replacement, and only between IDs the application supplied."""
    old, new = verifier.weakest_moment_id, verifier.replacement_moment_id
    alternates = {m for c in candidates for m in c.candidate_moment_ids} - set(best.moment_ids)
    if not (old in best.moment_ids and new in alternates and all(not redundant_with(new, x, pool) for x in best.moment_ids if x != old)):
        return best, None
    ids = [new if m == old else m for m in best.moment_ids]
    roles = {(new if m == old else m): r for m, r in best.roles.items()}
    score = score_bundle(ids, roles, [c.role for c in candidates], pool)
    if score.total < best.score.total - 0.05:  # typed guard: a replacement may not collapse the bundle
        return best, None
    return best.model_copy(update={'moment_ids': ids, 'roles': roles, 'score': score, 'expansion_log': best.expansion_log + [f'verifier: {old} → {new}']}), f'{old} → {new}'


def baseline(story: StoryIntent, images: list[Evidence], vectors: dict[str, np.ndarray], moment_of: dict[str, str],
             atoms_salience: dict[str, float], k: int, candidates: list[RoleCandidates], pool: Pool, emb: EmbeddingProvider) -> ScoredBundle:
    """E1 point-wise baseline: top-K *images* by similarity to the story intent, no roles, no dedupe."""
    if emb.cross_modal:
        query, how = emb.embed_texts([f'a photo of {story.intent}'])[0], 'SigLIP 2 similarity to the story intent'
    else:  # image-only fallback: the most *typical* photos, i.e. similarity to the album centroid
        centroid = np.mean([vectors[ev.id] for ev in images], 0)
        query, how = centroid / np.linalg.norm(centroid), 'fallback-embedding similarity to the album centroid'
    ranked = sorted(images, key=lambda ev: -float(vectors[ev.id] @ query))
    picked = [ev.id for ev in ranked[:k]]
    ids = [moment_of[s] for s in picked if s in moment_of]
    return ScoredBundle(seed='baseline', moment_ids=ids, roles={}, score=score_bundle(ids, {}, [c.role for c in candidates], pool),
                        expansion_log=[f'point-wise top-{k} images by {how}; no roles, no redundancy control', 'images: ' + ' '.join(picked)])


# ── orchestration ──────────────────────────────────────────────────────────
def weave(session_id: UUID, reasoning: ReasoningProvider | None = None, emb: EmbeddingProvider | None = None) -> WeaveResult:
    timings: list[StageTiming] = []
    clock = time.perf_counter()

    def lap(stage):
        nonlocal clock
        now = time.perf_counter()
        timings.append(StageTiming(stage=stage, ms=round((now - clock) * 1000)))
        clock = now

    session = store.get_session(session_id)
    from .transcription import ensure_transcripts
    ensure_transcripts(session)                      # every voice note is understood, even those kept as audio
    session = store.get_session(session_id)
    evidence = {str(f.id): extract(f, store.get_source(f.id)[1]) for f in session.fragments}
    images = [ev for ev in evidence.values() if ev.image is not None]
    if not images:
        raise ValueError('Add at least one photo to weave a memory.')
    lap('evidence')
    reasoning = reasoning or get_reasoning_provider(list(evidence.values()))
    usable = [ev for ev in evidence.values() if ev.image is not None or ev.text]
    atoms = build_atoms(reasoning.atomize(usable), evidence)
    covered = {str(s) for a in atoms for s in a.source_ids}
    if missing := [ev for ev in usable if ev.id not in covered]:  # every photo stays eligible, even if the model skipped it
        from .reasoning import HeuristicReasoning
        extra = build_atoms(HeuristicReasoning().atomize(missing), evidence)
        atoms += [a.model_copy(update={'id': f'atom_{len(atoms) + i + 1}'}) for i, a in enumerate(extra)]
    lap('atomize')
    emb = emb or get_embedding_provider()
    vectors = dict(zip([ev.id for ev in images], emb.embed_images([ev.image for ev in images])))
    lap('embed')
    salience = {str(s): a.salience for a in atoms for s in a.source_ids}
    duplicates = find_duplicates(images, vectors, emb.name, salience)
    dup_of = {str(s): g.id for g in duplicates for s in g.source_ids}
    moments = group_moments(atoms, evidence, vectors)
    kept = lambda m: [str(s) for s in m.image_source_ids if str(s) not in dup_of or any(g.kept_source_id == s for g in duplicates)]
    embedding = {}
    for m in moments:
        vs = [vectors[s] for s in kept(m)]
        embedding[m.id] = (lambda v: v / np.linalg.norm(v))(np.mean(vs, 0)) if vs else None
    atom_by_id = {a.id: a for a in atoms}
    text = {m.id: ' '.join([m.title, m.summary, *m.people, m.place or '', *m.moods] + [o for a in m.atom_ids for o in atom_by_id[a].objects + atom_by_id[a].themes]) for m in moments}
    stamps = [ev.captured_at for ev in images if ev.captured_at]
    if stamps:  # the day is the most common capture date; photos from other dates are thematic, not chronological
        main_day = max({t.date() for t in stamps}, key=lambda d: sum(t.date() == d for t in stamps))
        stamps = [t for t in stamps if t.date() == main_day]
    pool = Pool({m.id: m for m in moments}, embedding, text, dup_of, (max(stamps) - min(stamps)).total_seconds() if len(stamps) >= 2 else 0, stamps[0].date() if stamps else None)
    lap('moments')
    story = reasoning.reframe(moments, session.weave_instruction)
    if story.roles[0].role.lower() != 'anchor':
        story.roles[0].role = 'Anchor'
    candidates = retrieve(story, pool, emb)
    bundles = [expand(seed, name, candidates, pool) for seed, name in seeds(candidates, pool)]
    best = max(bundles, key=lambda b: b.score.total)
    lap('bundle')
    alternates = [pool.moments[m] for m in dict.fromkeys(x for c in candidates for x in c.candidate_moment_ids) if m not in best.moment_ids]
    report = reasoning.verify([pool.moments[m] for m in best.moment_ids], best.roles, alternates)
    selected, replacement = verify_and_replace(best, report, candidates, pool)
    lap('verify')
    moment_of = {str(s): m.id for m in moments for s in m.image_source_ids}
    base = baseline(story, images, vectors, moment_of, salience, len(selected.moment_ids), candidates, pool, emb)
    chosen_images = [evidence[s].image for m in selected.moment_ids for s in kept(pool.moments[m])]
    timed = [pool.moments[m].time_range for m in selected.moment_ids if pool.moments[m].time_range and pool.moments[m].time_range[0].date() == pool.main_day]
    uses_timeline = len({t[0] for t in timed}) >= 3 and (max(t[1] for t in timed) - min(t[0] for t in timed)).total_seconds() >= 45 * 60
    result = WeaveResult(session_id=session_id, created_at=datetime.now(timezone.utc),
        providers=ProviderInfo(reasoning=reasoning.mode, reasoning_model=reasoning.model, embeddings=emb.name, embedding_model=emb.model_id, cross_modal=emb.cross_modal),
        atoms=atoms, duplicate_groups=duplicates, moments=moments, story=story, role_candidates=candidates, seeds=bundles,
        selected=selected, verifier=report, verifier_mode=reasoning.mode, replacement=replacement, baseline=base,
        palette=palette(chosen_images), uses_timeline=uses_timeline, timings=[])
    lap('palette')
    from .art_director import direct
    words = {ev.id: ev.fragment.source_instruction or ev.text for ev in evidence.values() if ev.text or ev.fragment.source_instruction}
    words.update({ev.id: ev.text for ev in evidence.values() if ev.text})
    art = direct(result, {ev.id: ev.image for ev in images}, words)
    lap('art_direction')
    from .stickers import pick
    from .weave_models import ArtDirectionOut, StickerPickOut
    selected_moments = [pool.moments[m] for m in selected.moment_ids]
    texts = [*story.keywords, story.title, story.intent, *(w for w in words.values() if w),
             *(t for m in selected_moments for t in [m.title, m.summary, m.place or '', *m.moods]),
             *(t for a in atoms if any(s in a.source_ids for m in selected_moments for s in m.source_ids) for t in [*a.objects, *a.themes])]
    stickers = [StickerPickOut.model_validate(p.model_dump()) for p in pick(texts, result.palette)]
    lap('stickers')
    return result.model_copy(update={'timings': timings, 'art': ArtDirectionOut.model_validate(art.model_dump()), 'stickers': stickers,
                                     'day': pool.main_day})
