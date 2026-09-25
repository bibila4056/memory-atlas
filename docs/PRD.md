# Memory Atlas — Product Requirements Document

Status: **Product direction locked for the 48-hour MVP.**  
This document describes both the north-star product and the current experience principles. Implementation scope is defined separately in `MVP.md`.

## 1. Product statement

**Memory Atlas turns scattered photos, voice notes, and unfinished thoughts into grounded, personal visual memoirs — without taking authorship away from the person who lived them.**

Tagline:
> **Automate the curation, not the authorship.**

Core observation:
> **Capture is easy. Curation is work.**

People already record their lives across camera rolls, notes, messages, and voice recordings. What usually does not happen is the slow work of selecting, organizing, writing, designing, and preserving those fragments as something meaningful and beautiful enough to revisit.

Memory Atlas reduces that curation burden while preserving the user's actual photos, words, and voice.

## 2. Target user

Primary:
- People who already take many photos or save scattered thoughts but rarely make journals/scrapbooks because the process takes too much time.
- Users who care about aesthetics and personal expression but do not want to manually design every page.

Secondary:
- Travelers, students, creative professionals, couples/friends, and people who use journaling as reflection.

## 3. Jobs to be done

When I have photos, half-finished thoughts, and voice notes from a day or experience, I want to drop them somewhere with almost no setup, so that AI can organize and art-direct them into a beautiful memory I still recognize as mine.

When I revisit that memory later, I want to see not only a polished artifact but also where each part came from.

## 4. Product principles

### P1 — Low-friction capture
The user should not have to choose a template, palette, story structure, or "AI mode" before sharing the memory.

### P2 — Preserve authorship
Original photos, audio, and user-authored text are source evidence. AI may organize, select, lightly refine when explicitly allowed, or generate supporting art, but it should not silently replace the user's memory.

### P3 — Curation before generation
The hardest problem is deciding what belongs together and what role each fragment plays. The product must reason about the story before rendering art.

### P4 — Plan before render
The system creates a structured visual plan, then renders it deterministically. It does not ask an image model to invent an entire scrapbook page.

### P5 — Art in service of memory
Generated art should act as connective tissue: doodles, tape, brush marks, scene extensions, motifs, and transitions. It should not overwhelm the real evidence.

### P6 — Traceability
Every transformed or generated element should be traceable to the source material that inspired it.

### P7 — Aesthetic guidance, not upfront configuration
The product recommends a visual language after understanding the memory. The user can then accept or adjust the palette/art direction.

## 5. Default entry experience

### 5.1 Opening
The website opens as a closed physical diary.

Visual:
- deep moss/forest green cover
- slightly sun-faded yellowed edges
- subtle worn corners and tactile texture
- restrained aged-gold title/details
- premium, quiet, editorial rather than "vintage scrapbook"

Motion:
- first visit: cover opens and pages turn into the active diary
- approximately 1–1.3 seconds
- do not replay on every navigation
- respect reduced-motion preferences

### 5.2 Capture Desk — default landing page
After the diary opens, the user lands on the lightest possible conversational entry surface.

Opening prompt:
> **What do you want to remember today?**
or
> **What story do you want to tell me?**

The surface accepts:
- images
- voice
- text / diary writing
- short random notes

The user does **not** choose a visual style here.

The interaction should feel like dropping fragments onto a creative desk, not filling out a form and not chatting with a verbose assistant.

Primary CTA:
> **Weave this memory**

## 6. Weaving experience

Weaving is the signature intelligence step.

### 6.1 Fragment understanding
The system identifies:
- events / moments
- people
- places where inferable
- objects and visual anchors
- user-authored phrases
- emotional tone
- themes
- approximate chronology where evidence exists
- source quality / duplicate information

### 6.2 Moment grouping
Multiple fragments can describe the same moment.

Example:
- 3 coffee photos
- one line: "met Emily around noon"
- one voice sentence about the conversation

These become one moment:
> **Coffee with Emily**

### 6.3 Redundancy removal
The system avoids selecting visually or semantically repetitive evidence unless repetition is itself meaningful.

### 6.4 Story selection
The system chooses a small bundle that works together as a story.

Selection considers:
- semantic salience
- narrative-role coverage
- emotional coverage
- temporal coverage when applicable
- visual diversity
- source grounding
- redundancy

A simple MVP heuristic may score:
- 30% narrative-role coverage
- 20% salience
- 15% visual diversity
- 15% emotional coverage
- 10% temporal coverage
- 10% source grounding

This heuristic is an implementation choice, not a claim that it is a published algorithm.

### 6.5 Narrative roles
Roles help the system build a coherent bundle. They are flexible, not mandatory.

Possible roles:
- Anchor — what most defines the memory
- Human connection — a meaningful person/social moment
- Detail — a small concrete thing that makes the memory personal
- Transition — a change in mood/setting
- Closure — what remains at the end

A memory without a clear chronological structure may instead use thematic roles.

### 6.6 Art direction
After story selection, AI proposes:
- palette
- density
- photography ratio
- typography mood
- one dominant visual language
- per-element art treatment
- artistic tool routing

The user is shown the recommended palette and may switch among a small number of coherent alternatives **after** weaving.

### 6.7 Source preservation
Before rendering, every selected element receives:
- source IDs
- art treatment
- whether user text must remain verbatim
- whether source media must remain visible

## 7. Art treatment system

Default preference:
**PRESERVE > ANNOTATE > EXTEND > DISTILL**

### PRESERVE
Use original photo/text/audio representation without generative alteration.

### ANNOTATE
Keep the original source and add generated supporting elements around it.

Example:
- original coffee photo
- tiny hand-drawn coffee cup beside it
- subtle tape or handwritten arrow

### EXTEND
Keep a substantial part of the real source and extend the scene artistically.

Example:
- half real rainy street
- half line drawing / zine-like continuation

### DISTILL
Turn a supporting source/object into a derived artistic motif.

Example:
- umbrella from a photo becomes a doodle
- flowers become a brush-stroke motif

DISTILL should rarely be used for faces, identity-bearing photographs, or core factual evidence.

## 8. Artistic skills / tools

Art skills are renderers, not page designers.

Potential capabilities:
- tape collage treatment
- doodle/object extraction
- paper/zine scene extension
- watercolor/brush textures

The central Art Director sends each tool:
- source reference
- allowed transformation
- palette
- density
- visual role
- output constraints

All tools must follow a shared Art Direction Profile so multiple generated assets remain coherent.

## 9. Interactive Memory Spread

The final result is an interactive memoir spread, visually similar to an open editorial journal.

Preferred composition:
- 60–70% real photography/source evidence
- 15–25% typography/negative space
- 10–20% generated artistic layer

Possible elements:
- one hero photo
- 2–3 supporting images
- exact user quote
- lightly refined text only when user permits it
- one or two derived doodles / motifs
- tape / brush accents
- optional timeline when chronology materially helps the story

The timeline is **not required**. The system chooses it only when the source naturally supports a temporal narrative.

## 10. Provenance interaction

Hover or select any element:
- other content subtly fades
- selected element remains highlighted
- a small source card appears

Examples:

**Original photo**
- file/source
- date/time if available
- "Original preserved"

**Voice-derived quote**
- source: voice note
- timestamp
- play original audio

**Refined text**
- "Refined from your words"
- toggle Original / Refined

**Generated doodle**
- "Generated from Photo 07"
- treatment: DISTILL

This interaction is a core differentiator.

## 11. Archive / Calendar

Calendar is a secondary destination reached through the diary navigation.

Each saved date can show a **Memory Stamp**:
- tiny photo edge
- doodle
- color mark
- tape/ink motif

Hover may reveal 2–3 fragments.
Click opens the full saved spread.

The archive should feel like a visual memoir, not a productivity calendar.

## 12. North-star extensions

Not part of the 48-hour MVP:
- Echoes across time: surface semantically/emotionally related memories
- Parallel Day: permissioned shared memoir between two people
- persistent personal Style DNA from user choices
- long-term multimodal memory retrieval
- semantic search across the archive
- collaborative memory making
- location/music integrations
- mobile capture companion

## 13. Success criteria for the OA demo

The evaluator should understand within one minute:
1. what user problem exists
2. why AI is necessary
3. why the system is more than "prompt → pretty image"
4. how the product protects user authorship

The final visual result must be polished enough that the experience feels intentionally designed, not like a developer dashboard.
