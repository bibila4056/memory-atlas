# Memory Atlas — Repository Instructions

Memory Atlas turns scattered personal photos, voice, and text into grounded visual memoirs while preserving user authorship.

## Sources of truth

- Product intent and ideal product: `docs/PRD.md`
- Visual system, motion, and interaction: `docs/DESIGN.md`
- AI/system architecture and contracts: `docs/ARCHITECTURE.md`
- 48-hour implementation scope: `docs/MVP.md`
- Locked decisions and changes: `docs/DECISIONS.md`
- Shared domain vocabulary: `CONTEXT.md`
- Codex / Matt Pocock workflow: `docs/CODEX_WORKFLOW.md`

Read only the documents relevant to the current task.

## Non-negotiable product rules

1. The user enters through a diary-opening experience, then lands on a minimal conversational Capture Desk.
2. Calendar/Archive is a secondary destination, not the default landing page.
3. Preserve original photos, audio, and user-authored text as source evidence.
4. AI automates curation and art direction, not authorship.
5. Every generated or transformed element must retain provenance through `source_ids`.
6. Full memoir spreads are assembled by a deterministic renderer from a structured visual plan.
7. Image generation is used for derived artistic assets or bounded image transformations, not to regenerate the entire final page.
8. Machine-readable model outputs must use typed schemas.
9. Timeline is optional. Use it only when the source material genuinely supports a temporal story.
10. Do not add features outside `docs/MVP.md` without explicit approval.
11. If implementation reveals a product or architecture conflict, surface it before changing the docs or code.
12. Never silently rewrite a locked decision.


## Research-backed implementation rules

- Read `docs/RESEARCH.md` before implementing retrieval, Bundle Weaver, visual planning, or aesthetic reranking.
- When a ticket claims a paper-backed mechanism, implement a recognizable version of the mechanism and document deliberate simplifications.
- Do not replace research-backed modules with toy random/rule-only stubs in the final MVP without surfacing the change.
- Do not claim a model/paper is used unless the corresponding code path actually runs.
- Add a short module docstring or comment identifying the paper/mechanism being adapted where appropriate.
- Implement the lightweight evaluations in `docs/EVALS.md` before the final demo.

## Engineering defaults

- Frontend: Next.js + React + TypeScript
- Styling: Tailwind CSS
- Motion: Framer Motion
- Interactive spread: React Konva or a similarly deterministic layered canvas
- Backend: FastAPI + Python + Pydantic
- Multimodal reasoning: primary multimodal LLM with structured output
- Embeddings: SigLIP 2 for image/text retrieval where useful
- Vector storage: Qdrant local for MVP
- Transcription: a production speech-to-text API
- Art generation: one real runtime art tool in MVP; additional artistic assets may be cached for the demo

Prefer the simplest implementation that satisfies the MVP acceptance criteria.

## Coding-agent behavior

- Before implementing a ticket, read the relevant source-of-truth files.
- Preserve frontend/backend contracts unless the ticket explicitly changes them.
- Prefer small, testable changes.
- Run relevant tests/lint after each implementation slice.
- Do not "improve" product scope, visual direction, or architecture without approval.
