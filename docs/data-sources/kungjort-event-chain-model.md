# Kungjort: event-chain and process-history model

## Purpose

Kungjort notices must be mapped as events in longer administrative processes, not as isolated documents or one-off map points. A notice can describe a consultation, review, adoption, a correction, a renewed process, or another milestone concerning the same underlying planning or permitting matter. The same matter may change over time, be paused, be withdrawn, or restart with a revised proposal.

The archive must therefore preserve both:

1. **The notice as an immutable published source** (what was published, by whom, and when).
2. **The inferred process/event chain** that relates notices and versions to a continuing matter.

The event-chain model is a prerequisite for meaningful spatial analysis. A map should be able to show the current known state of a matter and also replay its history without counting every notice as a separate development.

## Core modelling rule

Do not equate a notice, a process, a plan version, and a geographic object.

Use four distinct concepts:

- **Notice** — one archived publication/source record. It is immutable; corrections or later publications create additional notice records.
- **Matter / case** — the continuing administrative matter, such as a municipality's detailed development plan process or an environmental permit case.
- **Process instance / proposal version** — a distinct iteration within a matter. A detailed plan that is substantially revised and sent through a new consultation/review cycle may need a new process instance, linked to the same matter.
- **Event** — the milestone or change described by a notice, such as consultation opened, review opened, plan adopted, decision gained legal force, process withdrawn, or process restarted.

A matter may contain several process instances; each process instance may contain many events; each event may be evidenced by one or more notices. A notice may also be relevant to more than one matter, but this should be explicit and evidence-based.

## Detailed development plan lifecycle

For detailed development plans, represent the lifecycle as a sequence of dated events, not a single status field:

1. Plan initiative / planning assignment (when present in the source material)
2. Consultation opened (**samråd**)
3. Consultation closed / consultation feedback stage completed (when evidenced)
4. Review opened (**granskning**)
5. Review closed (when evidenced)
6. Adoption decision (**antagande**)
7. Decision appealed / appeal handling (when evidenced)
8. Legal force (**laga kraft**)
9. Withdrawal, cancellation, expiry, or other termination (when evidenced)

Not every process will have every event, and the order can be irregular. Do not manufacture missing milestones or infer legal force from an adoption notice alone.

### Revisions and restarts

A plan can be changed after consultation or review. The revised proposal may be circulated again for consultation or review, and the planning process may effectively start over.

Represent this without overwriting the earlier history:

- Keep the same **matter_id** when there is strong evidence that the municipality is continuing the same planning matter.
- Create a new **process_instance_id** when a materially revised proposal begins a new procedural cycle or when the evidence indicates a new version/round.
- Link the new process instance to the previous one with a typed relation such as `revises`, `restarts_after`, or `supersedes`.
- Keep all previous events, notice records, and spatial footprints. Mark earlier proposals as superseded or withdrawn only when a source supports that interpretation.
- A second consultation or review is a new event, not a duplicate of the first one. Preserve round numbers where they can be extracted; otherwise retain an unknown round rather than guessing.

If the evidence is insufficient to decide whether a notice belongs to the same matter or a new matter, keep the records separate and create a candidate relationship for later review. False merges are more damaging than temporarily unlinked records.

## Suggested logical entities and fields

These are conceptual fields, not a commitment to a physical database schema yet.

### Notice

- `notice_id`: stable archive identifier for one publication
- source identifier / source URL / source batch
- publishing authority and source publication date
- captured/ingested timestamp
- original title and source text location (private Azure storage)
- extracted reference numbers, plan names, municipality, property identifiers and place names
- immutable source checksum where available

### Matter

- `matter_id`: stable identifier for the continuing administrative matter
- matter type (detailed plan, permit, infrastructure project, nature protection, etc.)
- responsible authority
- municipality / jurisdiction
- normalized case reference(s), plan designation/name and aliases
- first-seen and last-seen timestamps
- linkage confidence and evidence

### Process instance / proposal version

- `process_instance_id`
- parent `matter_id`
- version / round label, if supported by evidence
- start and end dates (with date precision)
- process state as a derived view, not a replacement for events
- predecessor/successor process instance IDs and relation type
- proposal-specific spatial footprint version

### Event

- `event_id`
- `matter_id` and optional `process_instance_id`
- event type and event date
- date role (publication date, decision date, consultation period start/end, legal-force date, etc.)
- one or more supporting `notice_id` values
- extraction method, confidence, and evidence snippet/reference
- whether the event is directly stated or inferred

### Spatial footprint

- footprint ID and linked matter/process instance
- geometry, CRS, source and source date
- spatial role (plan boundary, affected property, approximate place, corridor, study area, etc.)
- validity period / proposal version
- positional accuracy and geocoding method
- evidence and confidence

A matter's location must not be treated as timeless. A revised plan may have a different boundary, and a linear infrastructure project may have several alternative corridors. Preserve geometries per proposal/version and distinguish an exact boundary from an approximate geocoded place.

## Linking notices into chains

Use a staged, explainable matching process.

### Strong linkage evidence

- same explicit case number or plan designation, in the same authority/jurisdiction
- explicit references such as "revised proposal", "new consultation", "previously consulted", or a cited earlier decision
- same named plan and authority, supported by compatible dates and other identifiers

### Supporting evidence

- same municipality and authority
- matching normalized plan name or project name / aliases
- same or overlapping property identifiers
- compatible location or geometry
- plausible chronology and lifecycle transition

### Insufficient evidence on its own

- same keyword (for example "detaljplan")
- same municipality
- geographic proximity or overlapping approximate geocoding
- similar titles without corroborating identifiers

Each proposed link should record its relation type, confidence, and the evidence that caused it. Automatic matching should not silently merge matters. Low-confidence links should remain candidates for review.

## Temporal model

Keep separate dates that answer different questions:

- source publication date
- event/decision date
- consultation or review period start/end
- date first captured by the archive
- date a later source corrected, superseded, or clarified an earlier event

This supports both "what was known at the time?" and "what do we now know happened?" queries. Missing dates remain missing; do not substitute the ingestion date for the event date.

## Mapping and counting rules

- Map a **matter** as the continuing subject, but expose its event history and proposal versions.
- Map **process-instance footprints** when the boundary changes between proposal versions.
- Map a notice as an event marker only when that is useful; do not make every notice look like a separate project.
- Distinguish exact geometries from approximate geocoding and from municipality-only locations.
- Count unique matters, process instances, events, and notices separately. Never present notice count as project count.
- For a "current" map, derive current state from the event history and source evidence. For a historical map, allow a date/time cut-off and show what was known then.
- A later adoption or legal-force event must not erase earlier consultation/review events from the historical view.

## Pilot scope

Start with detailed development plans because their lifecycle gives a concrete test of the model.

1. Select a small sample of notices containing terms such as `detaljplan`, `samråd`, `granskning`, `antagande`, and `laga kraft`.
2. Extract plan designation/name, municipality, authority, case reference, procedural dates, and explicit references to earlier rounds.
3. Manually label a gold-standard set of notice-to-matter and notice-to-process-instance links.
4. Test the matcher against that set, reporting precision and unresolved candidates rather than only the number of links found.
5. Build event timelines for examples with multiple rounds, revisions, withdrawals, and restarts.
6. Only then connect process instances to plan geometries and test whether boundaries change across rounds.

The current aggregate quality report is useful for choosing candidate terms, but it does not contain notice-level identifiers or text and cannot itself establish event chains. The private source records in Azure must be used for the pilot; GitHub artifacts should remain aggregate-only.

## Acceptance criteria before spatial matching is scaled up

- Every notice remains individually addressable and immutable.
- A matter can contain multiple process instances and repeated consultation/review rounds.
- A restart or revision never overwrites the earlier process history.
- Links have explicit evidence, relation type, and confidence.
- Uncertain cases remain unlinked candidates rather than being force-merged.
- Spatial footprints are versioned and tied to the process instance they describe.
- Reports distinguish unique notices, events, process instances, and matters.
- A timeline can be reconstructed at a historical cut-off date.

## Implementation sequence

1. Document and agree on the event-chain vocabulary and entity boundaries.
2. Inspect the actual Kungjort source fields and a small private sample in Azure to establish which identifiers and dates are available.
3. Add extraction for event type, case references, plan designation, process round, and temporal fields without changing the existing ingestion history.
4. Create candidate linkage records and a reviewable gold-standard test set.
5. Evaluate matching quality before enabling automatic chain construction.
6. Add versioned spatial footprints and map views after the chain model is stable.

This design deliberately separates source ingestion, event extraction, entity resolution, and spatial matching. Each layer can be tested independently, and no stage should destroy the source history.
