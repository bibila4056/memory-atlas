# Memory Atlas — AI Evaluation Plan

The OA does not require research-grade experiments, but the project should contain enough evaluation to show that architectural choices are evidence-driven rather than decorative.

## E1. Bundle selection: point-wise baseline vs BundleWeaver-lite

Create 3–5 small test cases from personal/demo fragments.

For each case, manually define:
- important moments
- redundant photos
- expected complementary roles
- unacceptable hallucinated evidence

Compare:

### Baseline
Top-K retrieval using only SigLIP 2 similarity.

### Proposed
BundleWeaver-lite:
- role-aware retrieval
- redundancy/diversity control
- whole-bundle VLM verification

Record:
- Set Precision
- Set Recall
- Set F1
- redundancy count
- human "coherent story?" yes/no

These set metrics mirror the style of bundle-level evaluation used by the BundleWeaver repository, but our tiny demo evaluation is not directly comparable to IBCBench.

## E2. Whole-bundle VLM rubric

For each selected bundle, score 1–5:
- coverage: does it capture the essential story?
- coherence: do items belong together?
- complementarity: do selected items add different information?
- groundedness: can all claims be traced to submitted evidence?
- visual diversity: is the bundle more useful than near-duplicate burst shots?

Store the rubric output as structured JSON.

## E3. Provenance / authorship invariants

Automated checks:
- 100% of displayed source-derived elements have non-empty `source_ids`
- "verbatim" text exactly matches source text/transcript substring
- PRESERVE image elements point to original file bytes
- generated assets identify at least one grounding source
- no inferred time/place is rendered as fact when evidence is absent

These are product-safety correctness tests, not model-quality metrics.

## E4. Layout quality

For 2–3 candidate VisualPlans:
- reject overlap/safe-margin violations
- reject illegible text sizes
- reject layouts with no clear visual anchor
- reject excessive generated-art ratio

Then use pairwise multimodal critique with a fixed rubric:
- hierarchy
- balance
- whitespace
- coherence with palette
- relationship between source photography and generated art
- legibility
- "does this feel like a personal memoir rather than an AI collage?"

This is an inference-time product approximation inspired by aesthetic-preference research such as AesthetiQ; it is not a reproduction of its DPO training.

## E5. Latency logging

Log per stage:
- transcription
- atomization
- embedding
- bundle weaving
- visual planning
- art generation

For the OA recording:
- cache generative-art output
- show real timings separately if useful
- do not pretend cached generation was live
