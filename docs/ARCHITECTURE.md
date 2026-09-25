# Memory Atlas — Technical Architecture

## 1. Architectural principle

The system is a pipeline, not a single prompt:

**Raw fragments → structured understanding → story bundle → visual plan → bounded art generation → deterministic interactive render**

This separation is deliberate:
- it makes selection inspectable
- it keeps source fidelity
- it reduces hallucinated memory content
- it lets art tools specialize
- it preserves interactivity and provenance

## 2. High-level components

### A. Multimodal Intake
Inputs:
- images
- text
- voice

Responsibilities:
- store source media
- extract metadata where available
- transcribe voice
- assign stable source IDs

### B. Memory Atomizer
A multimodal reasoning model converts fragments into typed internal records.

A Memory Atom may contain:
- source IDs
- event/moment candidate
- people
- place
- objects
- mood/themes
- chronology
- salience
- exact user text
- preservation constraints

The original source is always retained.

### C. Moment Grouper
Clusters atoms that refer to the same lived moment.

Example:
3 coffee images + one text fragment + one voice phrase
→ one "Coffee with Emily" moment.

### D. Bundle Weaver
Selects a complementary story bundle rather than ranking items independently.

Pipeline:
1. propose story intent and flexible narrative roles
2. retrieve candidate evidence per role
3. remove redundancy
4. score bundle-level coverage/diversity
5. multimodal verifier reviews the whole bundle
6. replace weak/redundant elements if necessary

MVP heuristic:
- narrative-role coverage: 0.30
- salience: 0.20
- visual diversity: 0.15
- emotional coverage: 0.15
- temporal coverage: 0.10
- source grounding: 0.10

Weights are tunable implementation heuristics.

### E. Visual Director
Inputs:
- selected story bundle
- suggested palette
- user text-preservation preference
- visual constraints

Outputs a typed Visual Plan:
- page template
- palette
- source placements
- typography roles
- art treatments
- generated asset requests
- provenance links

The model must not output arbitrary HTML/CSS.

### F. Art Tool Router
Maps each generated asset request to one specialized capability.

Possible tools:
- Doodle Tool
- Tape Tool
- Zine / Scene Extension Tool

Each receives a shared Art Direction Profile.

### G. Deterministic Renderer
Frontend composes:
- real images
- real text
- generated transparent assets
- paper/tape textures
- layout geometry

The final spread is not flattened into one generated image.

### H. Provenance Resolver
Every VisualElement carries `source_ids`.

Interaction can retrieve:
- original photo
- original text
- audio clip/timestamp
- transformation mode

## 3. Suggested stack

### Frontend
- Next.js
- React
- TypeScript
- Tailwind CSS
- Framer Motion
- React Konva for layered spread interaction, or HTML/SVG if sufficient

### Backend
- FastAPI
- Python
- Pydantic
- local file storage for demo assets

### Reasoning
- Primary multimodal LLM API with structured JSON output
- Use Sol for the majority of implementation/runtime reasoning if available in the user's environment
- A higher-cost model may be used sparingly for architecture/design review, not as a dependency of the MVP

### Speech
- production speech-to-text API

### Retrieval
- SigLIP 2 for image/text embeddings
- Qdrant local for vectors/metadata

Qdrant is optional if retrieval complexity threatens the 48-hour deadline. A small in-memory vector index is an acceptable fallback if the interface stays the same.

### Art generation
MVP:
- one real runtime art capability, preferably a doodle/annotation tool
- additional tape/zine assets may be cached for demo reliability

## 4. Core schemas

### SourceFragment
```ts
type SourceFragment = {
  id: string;
  modality: "image" | "text" | "audio";
  uri: string;
  timestamp?: string;
  originalText?: string;
};
```

### MemoryAtom
```ts
type MemoryAtom = {
  id: string;
  sourceIds: string[];
  event: string;
  people: string[];
  place?: string;
  objects: string[];
  moods: string[];
  themes: string[];
  timestamp?: string;
  salience: number;
  verbatimText?: string;
  mustPreserve: boolean;
};
```

### Moment
```ts
type Moment = {
  id: string;
  title: string;
  atomIds: string[];
  sourceIds: string[];
  summary: string;
  moods: string[];
  timeRange?: [string, string];
};
```

### NarrativeRole
```ts
type NarrativeRole = {
  role: string;
  intent: string;
  candidateMomentIds: string[];
  selectedMomentId?: string;
};
```

### ArtTreatment
```ts
type ArtTreatment =
  | "PRESERVE"
  | "ANNOTATE"
  | "EXTEND"
  | "DISTILL";
```

### VisualElement
```ts
type VisualElement = {
  id: string;
  kind: "photo" | "quote" | "caption" | "doodle" | "tape" | "brush";
  sourceIds: string[];
  treatment: ArtTreatment;
  x: number;
  y: number;
  width: number;
  rotation?: number;
  zIndex: number;
  text?: string;
  assetUri?: string;
};
```

### MemoirPlan
```ts
type MemoirPlan = {
  title: string;
  pageType: string;
  palette: string[];
  visualLanguage: string;
  elements: VisualElement[];
  usesTimeline: boolean;
};
```

## 5. API surface

Minimal:
- `POST /api/session`
- `POST /api/transcribe`
- `POST /api/ingest`
- `POST /api/weave`
- `POST /api/compose`
- `POST /api/generate-asset`
- `GET /api/source/:sourceId`

Frontend/backend types must remain stable once the visual shell is built.

## 6. Grounding rules

- No generated sentence may be presented as the user's original words.
- Exact quotes require a direct source link.
- If the system lightly rewrites text, store original and refined versions separately.
- Generated visual motifs must identify the source(s) that grounded them.
- Faces/identity-bearing hero photos should default to PRESERVE or ANNOTATE.
- The system must not fabricate a precise time/place when source evidence is absent.

## 7. Runtime reliability for the OA

- cache art-generation results used in the recorded demo
- keep deterministic fallback VisualPlans
- never depend on a live image-generation call during the final recording
- log selected source IDs and role assignments for debugging
