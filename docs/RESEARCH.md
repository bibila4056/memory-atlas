# Memory Atlas — Research Grounding

Status: **Required reference for AI architecture.**

Memory Atlas is a product prototype, not a paper reproduction. However, the AI architecture should be grounded in recent, real research rather than invented "agent" terminology.

The rule is:

> If we claim a research-backed mechanism in the demo, the code must implement a recognizable version of that mechanism, and the README/demo must state clearly what was reproduced, simplified, or only inspired by.

## R1. Image Bundle Composition / BundleWeaver — primary MVP research anchor

**Paper**  
Rong Shan et al.  
*Weaving Visual Narratives: Agentic Image Bundle Composition Beyond Atomic Visual Matching*  
arXiv:2608.28695, accepted to EMNLP 2026 Main Conference.

**Official code**  
`https://github.com/LaVieEnRose365/Image-Bundle-Composition`  
Repository license: Apache-2.0.

### Key idea
Personal-photo selection is not always a point-wise ranking problem. A useful result can be a compact set of images whose value comes from the **relations among the set**.

BundleWeaver implements:
1. task reframing / anchor extraction
2. diverse seed initialization
3. adaptive expansion by identifying a missing relational role
4. whole-bundle VLM verification

### Memory Atlas adaptation — MUST IMPLEMENT
The MVP should implement a small-scale version:

1. **Story reframing**
   - infer the story intent from all submitted fragments
   - propose flexible narrative roles

2. **Diverse seed / candidate retrieval**
   - retrieve multiple candidates rather than always taking one top image
   - discourage near-duplicate photos

3. **Missing-role expansion**
   - inspect the partial story bundle
   - identify what complementary role/evidence is missing
   - retrieve a targeted candidate for that role

4. **Whole-bundle verification**
   - evaluate selected moments jointly for:
     - coverage
     - coherence
     - redundancy
     - groundedness
     - visual diversity
   - replace one weak candidate when needed

### Deliberate simplifications
Do NOT claim to reproduce the full paper:
- no large 109K-image pool
- no full beam-search implementation unless time permits
- no spatiotemporal pruning infrastructure required
- no IBCBench-scale evaluation

We call this implementation **BundleWeaver-lite** and explicitly cite the original framework.

---

## R2. SigLIP 2 — actual open-source multimodal retrieval model

**Paper**  
Michael Tschannen et al.  
*SigLIP 2: Multilingual Vision-Language Encoders with Improved Semantic Understanding, Localization, and Dense Features*  
arXiv:2502.14786.

**Model**  
`google/siglip2-base-patch16-256` on Hugging Face.  
License: Apache-2.0.

### Key idea
SigLIP 2 is a multilingual image-text encoder supporting image-text retrieval and improved semantic visual representations.

### Memory Atlas usage — MUST BE REAL IF INCLUDED IN DEMO
Use the actual model, not an LLM-generated embedding placeholder, for:
- image embeddings
- text-query embeddings
- candidate retrieval for story roles
- optional near-duplicate/diversity calculations

### Fallback
If local hardware/runtime makes SigLIP 2 infeasible during the 48-hour build:
- preserve the `EmbeddingProvider` interface
- document the fallback honestly
- do not claim SigLIP 2 was used unless it actually ran

---

## R3. PhotoBench — research motivation for personal photo reasoning

**Paper**  
Tianyi Xu et al.  
*PhotoBench: Beyond Visual Matching Towards Personalized Intent-Driven Photo Retrieval*  
arXiv:2603.01493 (2026).

### Key finding relevant to Memory Atlas
Personal albums involve more than visual similarity. Useful retrieval can depend on:
- visual semantics
- temporal metadata
- social identity
- event context
- user intent

The paper reports limitations of unified embedding-only retrieval for such constraints and motivates agentic multi-source reasoning.

### Memory Atlas implication
Do not treat SigLIP similarity as the final decision-maker.

The retrieval stack should combine:
- embedding candidates
- structured Memory Atom metadata
- narrative role
- whole-bundle reasoning

PhotoBench is architectural motivation, not a method we claim to reproduce.

---

## R4. V-Mem — long-term multimodal memory, primarily North Star

**Paper**  
Dingyi Kang et al.  
*V-Mem: Modality-Routed Retrieval for Long-Term Multimodal Agentic Memory*  
arXiv:2608.01543 (2026).

**Official code**  
`https://github.com/Dingyi-Kang/V-Mem`  
License: MIT.

### Key idea
Naive similarity retrieval can fail because of:
- modality gap
- similarity–relevance gap

V-Mem routes retrieval by target modality and uses generated search anchors to bridge these gaps.

### Memory Atlas usage
For the 48-hour MVP, V-Mem is **not required** because we are weaving one short session/day.

For the ideal product, use this as the main reference when implementing:
- cross-day retrieval
- Echoes
- long-term mixed text/image memory
- searching images from text-only recollection

Do not add long-term V-Mem infrastructure to the MVP unless P0 is already stable.

---

## R5. LayoutAgent — plan before render

**Paper**  
Zezhong Fan et al.  
*LayoutAgent: A Vision-Language Agent Guided Compositional Diffusion for Spatial Layout Planning*  
arXiv:2509.22720 (2025).

### Key idea
High-quality visual composition benefits from explicit spatial planning before rendering rather than asking a generative model to solve layout implicitly.

### Memory Atlas adaptation — MUST IMPLEMENT AS ARCHITECTURAL PRINCIPLE
Use:
- a structured `VisualPlan`
- explicit element geometry
- semantic relationships / hierarchy
- deterministic frontend rendering

Do NOT claim to reproduce:
- its compositional diffusion method
- its foreground-conditioned generation pipeline

Our use is **plan-first architecture inspired by LayoutAgent**.

---

## R6. AesthetiQ — aesthetic quality is not only geometric correctness

**Paper**  
Sohan Patnaik et al.  
*AesthetiQ: Enhancing Graphic Layout Design via Aesthetic-Aware Preference Alignment of Multi-modal Large Language Models*  
CVPR 2025.

### Key idea
A technically valid layout is not automatically aesthetically preferred. AesthetiQ explicitly aligns layout generation with aesthetic preference.

### Memory Atlas adaptation
We are NOT reproducing AAPA/DPO training.

Instead, the MVP can use an inference-time approximation:
1. generate 2–3 candidate `VisualPlan`s
2. reject plans that violate deterministic layout constraints
3. use a multimodal judge with an explicit aesthetic rubric
4. choose the strongest candidate
5. keep the judge score/log for debugging

This should be described as **inspired by aesthetic-aware preference alignment**, not as AesthetiQ reproduction.

---

# Research-backed MVP architecture

```text
Photos + text + voice
        │
        ▼
Multimodal Atomizer
(structured evidence)
        │
        ▼
Moment Grouper
        │
        ▼
BundleWeaver-lite
  ├─ flexible story roles
  ├─ SigLIP 2 candidate retrieval
  ├─ diversity / redundancy checks
  └─ whole-bundle VLM verification
        │
        ▼
Visual Director
(plan-first; typed VisualPlan)
        │
        ├─ 2–3 candidate plans
        ├─ layout constraints
        └─ aesthetic reranking
        │
        ▼
Specialized Art Tool(s)
        │
        ▼
Deterministic Renderer
        │
        ▼
Interactive provenance-grounded memoir
```

# Research honesty rules

1. Never write "state of the art" in the product/demo without specifying the task/paper and what we actually implement.
2. Never claim to "use" a paper merely because we copied its terminology.
3. If code is adapted from a public repository, preserve its license/attribution requirements.
4. Separate:
   - **reproduced/adapted mechanism**
   - **architectural inspiration**
   - **future-work reference**
5. Keep the system small enough to finish; technical credibility comes from implementing a few mechanisms correctly, not from adding more named agents.
