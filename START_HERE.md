# Memory Atlas — Start Here

This file is the shortest path from the starter pack to the first Codex planning session.

## 1. Unzip and rename

Rename the folder to:

```text
memory-atlas
```

Open Terminal and enter the folder:

```bash
cd /path/to/memory-atlas
```

## 2. Initialize Git locally

```bash
git init
git add .
git commit -m "freeze Memory Atlas product spec v0.1"
```

This creates the first local checkpoint. It does **not** upload anything yet.

## 3. Create a private GitHub repository

Create a **Private** repository named:

```text
memory-atlas
```

Do not initialize it with another README, .gitignore, or license.

Then run the commands GitHub gives you. They will look similar to:

```bash
git remote add origin git@github.com:YOUR_USERNAME/memory-atlas.git
git branch -M main
git push -u origin main
```

## 4. Open the repo in Codex

Open the local `memory-atlas` folder as the Codex workspace.

Do **not** ask Codex to build the app yet.

## 5. Install Matt Pocock / AI Hero skills

From the repo root:

```bash
npx skills@latest add mattpocock/skills
```

Then in Codex:

```text
/setup-matt-pocock-skills
```

For this 48-hour solo project, choose the lowest-overhead issue-tracking option available.

Confirm Codex-critical instructions live in `AGENTS.md`.

## 6. First Codex message

Send this exactly:

```text
Before writing any application code, read:

- AGENTS.md
- CONTEXT.md
- docs/PRD.md
- docs/DESIGN.md
- docs/ARCHITECTURE.md
- docs/MVP.md
- docs/DECISIONS.md
- docs/RESEARCH.md
- docs/EVALS.md
- docs/CODEX_WORKFLOW.md

Treat docs/PRD.md as the authoritative product definition,
docs/MVP.md as the hard 48-hour scope boundary,
docs/DESIGN.md as the visual source of truth,
docs/ARCHITECTURE.md as the technical source of truth,
and docs/DECISIONS.md as locked decisions.

Do not redesign the product.
Do not add features.
Do not write application code yet.

First:
1. summarize the product in 8-12 bullets,
2. identify only contradictions, missing implementation-critical details,
   or acceptance criteria that are too vague,
3. distinguish true blockers from optional improvements,
4. do not modify files until I approve.

After that, we will run /grill-with-docs only on the unresolved blockers.
```

## 7. Review Codex's understanding

Before continuing, verify that Codex correctly understands:

- landing page = conversational Capture Desk, not Calendar
- user does not choose style before uploading
- Weaving includes understanding, grouping, de-duplication, selection,
  narrative structure, art direction, and source preservation
- full memoir page is deterministic, not one AI-generated bitmap
- original words/photos/audio remain traceable
- timeline is optional
- Calendar is secondary Archive
- no features outside `docs/MVP.md`

If any of these are wrong, correct them before moving on.

## 8. Run Grill With Docs

Then say:

```text
/grill-with-docs

Use the existing Memory Atlas documents as the starting point.
Only question unresolved implementation-critical ambiguities.

Prioritize:
1. exact Weaving selection behavior,
2. narrative-role flexibility,
3. preservation vs annotate/extend/distill boundaries,
4. VisualPlan schema and renderer contract,
5. runtime vs cached art-tool behavior,
6. provenance requirements,
7. MVP acceptance criteria.

Do not reopen locked product decisions unless they directly contradict
another requirement or make the MVP impossible.
Ask in small rounds, not one giant questionnaire.
```

Spend no more than ~30-45 minutes on this step.

## 9. Freeze the clarified plan

After the grilling session:
- review any edits to `CONTEXT.md`
- review any ADRs under `docs/adr/`
- record new locked decisions in `docs/DECISIONS.md`

Then commit:

```bash
git add .
git commit -m "clarify Memory Atlas implementation spec"
git push
```

## 10. Convert plan into implementation work

In the **same Codex conversation**, run:

```text
/to-spec
```

Review the spec.

Then:

```text
/to-tickets
```

Recommended implementation order:

1. scaffold + typed contracts + deterministic demo fixture
2. cover-opening animation + Capture Desk shell
3. Weaving UI with mocked structured data
4. interactive Memory Spread + provenance using fixture
5. voice transcription
6. Memory Atom extraction
7. moment grouping + Bundle Weaver
8. VisualPlan generation
9. one runtime artistic tool
10. Archive/Calendar shell
11. integration + polish
12. demo reliability + recording

## 11. Implement one ticket at a time

For each ticket:

```text
/implement
```

After each stable milestone:

```bash
git add .
git commit -m "describe what was completed"
git push
```

Do not let the coding agent silently expand scope.

## 12. Before recording

Run:

```text
/code-review
```

Ask it to review against:
- docs/MVP.md
- docs/DECISIONS.md
- provenance invariants
- source fidelity
- VisualPlan/render separation
- accidental scope creep

Use cached image-generation outputs for the recording so the demo is deterministic.
