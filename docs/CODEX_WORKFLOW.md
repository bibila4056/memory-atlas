# Memory Atlas — Codex + Matt Pocock Skills Workflow

This project uses Matt Pocock's skills as a planning/engineering workflow, not as the product runtime.

## Why use them

The useful chain is:

`grill-with-docs → to-spec → to-tickets → implement → code-review`

`grill-with-docs` is valuable because it interviews the human, settles vocabulary, and records durable terms/architectural decisions in the repo. The project is large enough to span multiple coding sessions, so a written spec/tickets are useful.

## Recommended installation

From the repo root:

```bash
npx skills@latest add mattpocock/skills
```

Installing the full set avoids the known failure mode where `grill-with-docs` loads without its `grilling` and `domain-modeling` dependencies.

Then run once:

```text
/setup-matt-pocock-skills
```

For a 48-hour solo build, choose the issue-tracking option that creates the least overhead. If the repo already has a GitHub remote and you want the specs/tickets there, use GitHub. Otherwise local markdown is acceptable.

Ensure the setup writes its agent block to **AGENTS.md** for Codex. If a stale `CLAUDE.md` exists, verify it did not put Codex-critical instructions there instead.

## First Codex session

Do NOT ask Codex to build the app immediately.

Start with:

```text
Read AGENTS.md, CONTEXT.md, docs/PRD.md, docs/DESIGN.md,
docs/ARCHITECTURE.md, docs/MVP.md, docs/DECISIONS.md,
docs/RESEARCH.md, and docs/EVALS.md.

We are preparing a 48-hour MVP of Memory Atlas.

Use /grill-with-docs to stress-test only the unresolved or ambiguous
parts of this plan. Do not redesign the product and do not propose new
features unless an existing requirement is internally inconsistent or
unbuildable.

Focus your questions on:
1. exact Weaving behavior and selection criteria,
2. boundary between original evidence and generated art,
3. visual-plan contracts,
4. runtime vs cached art-tool behavior,
5. acceptance criteria that are still too vague,
6. frontend/backend seams.

Treat the locked entries in docs/DECISIONS.md as settled unless you find
a direct contradiction.

Ask in rounds, not all questions at once.
```

### Verify the skill loaded correctly
If it dumps a giant list of questions or fails to update domain docs, ask:
> Which skills did you load for `/grill-with-docs`?

It should have access to the grilling and domain-modeling dependencies.

## After grilling

Review:
- changes to `CONTEXT.md`
- any ADRs written under `docs/adr/`
- conversation decisions that did not become ADRs

Do not clear/compact the conversation.

Then run:

```text
/to-spec
```

The spec must contain only decisions actually made. Pay special attention to:
- test seams
- out-of-scope section
- exact behavior of Weaving
- source/provenance invariants

Because this build spans multiple sessions, continue:

```text
/to-tickets
```

Tickets should be tracer-bullet sized and ordered to preserve demo viability.

## Suggested ticket sequence

1. Project scaffold + typed contracts + mocked fixture
2. Diary cover + Capture Desk visual shell
3. Weaving UI using mocked structured data
4. Interactive Memory Spread + provenance UI using fixture
5. Voice transcription
6. Memory Atom extraction
7. Moment grouping + Bundle Weaver selection
8. Visual Plan generation
9. One runtime art tool
10. Calendar/Archive shell
11. Integration/polish
12. Demo reliability + recording fixture

## Implementation rule

For each ticket, use:

```text
/implement
```

Then review before moving on.

Critical instruction:
**Preserve existing frontend/backend contracts unless the ticket explicitly changes them.**

## Review

Before recording:

```text
/code-review
```

Ask it to review specifically against:
- `docs/MVP.md`
- locked decisions
- provenance invariants
- source-text/source-photo fidelity
- visual plan/render separation
- accidental scope creep

## Human checkpoints

Stop for manual approval:
1. after grilling
2. after spec
3. after visual shell
4. after first real Weaving result
5. after first final Memory Spread
6. before recording

## Important mental model

Matt Pocock skills help the **coding agent work rigorously**.
They are not runtime dependencies of Memory Atlas.

Likewise, development-time artistic skills are not automatically available
to the deployed product. A runtime art tool must be implemented explicitly
through an image-generation/editing API or a service with equivalent behavior.
