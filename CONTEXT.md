# Memory Atlas — Domain Vocabulary

This file is a glossary, not a product spec.

**Fragment**  
One raw user-provided piece of evidence: a photo, text note, diary paragraph, or voice recording.

**Memory Atom**  
An internal structured representation extracted from one or more fragments. It records what the system understands about an event or detail while preserving links to the original sources. It is not a user-facing term.

**Moment**  
A coherent part of the lived experience represented by one or more memory atoms, such as "coffee with Emily" or "walking home in the rain."

**Story Bundle**  
The small set of complementary moments and fragments selected to form one memoir entry. The goal is bundle-level narrative coherence, not independent top-ranked items.

**Narrative Role**  
The purpose a selected moment plays in the story, such as anchor, human connection, detail, transition, or closure. Roles are flexible and not every story needs every role.

**Weaving**  
The AI process that understands fragments, groups them into moments, removes redundancy, selects a story bundle, decides narrative roles, and proposes an art direction.

**Art Direction Profile**  
A visual system for the memoir: palette, density, photography ratio, texture, typography, and allowed artistic treatments. The user may accept or adjust the recommended profile after weaving.

**Art Treatment**  
How one source becomes part of the final page:
- PRESERVE: original source remains unchanged
- ANNOTATE: original remains; generated elements are layered around it
- EXTEND: original remains partially visible; generated art extends its scene
- DISTILL: a derived artistic representation is created from the source

**Visual Plan**  
A structured, machine-readable layout plan describing page type, palette, source placement, text placement, artistic assets, treatment modes, and provenance.

**Memory Spread**  
The final interactive visual memoir entry assembled from original sources and bounded AI-generated elements.

**Provenance**  
The trace from any memoir element back to the original photo, voice clip, or text that grounded it.

**Archive**  
The notebook/calendar view used to revisit previously created memory spreads. It is secondary to the Capture Desk.

**Memory Stamp**  
A small, aesthetic preview attached to an archived date. It hints at the day through a few motifs, colors, or photo fragments without reproducing the full spread.
