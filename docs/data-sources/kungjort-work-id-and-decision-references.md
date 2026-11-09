# Kungjort: work IDs and planning-decision references

## Purpose

This note defines the reference hierarchy for linking Kungjort notices into Swedish municipal detailed-planning processes. It incorporates the operational convention that a plan is commonly identified in samhällsplanering by its municipal work/case ID, for example `KLF2023/1308`.

The work ID is the primary practical key for finding the planning matter across notices and municipal records. A protocol reference such as `2023-10-23 (§ 21)` is valuable supporting evidence for a specific decision event, but it is not normally the plan's primary identifier.

## Reference hierarchy

### 1. Municipal work ID — primary matter reference

Example: `KLF2023/1308`.

Treat a clearly identified municipal work ID as the strongest practical reference for a planning matter, subject to authority/jurisdiction context.

Store:
- `work_id_raw`: exact source form, e.g. `KLF2023/1308`
- `work_id_normalized`: conservative normalized form used for exact matching
- `work_id_authority`: municipality/authority that issued or uses the ID
- `work_id_evidence`: source notice and field/text location where it was found
- `work_id_role`: whether it is explicitly labelled as a work/case reference or only detected in text

Do not strip meaningful letters, digits, slash structure, or year components. Normalize case and surrounding whitespace only. Do not match on a numeric suffix alone. Never assume two authorities' identical-looking IDs refer to the same matter.

A repeated exact work ID within the same authority is a high-strength candidate link between notices. It still does not by itself decide whether notices describe the same process instance, a later revision, a new consultation round, or separate sub-matters under one administrative file.

### 2. Plan designation and plan name — corroborating identity

Examples include the formal plan designation, plan name, property designation and descriptive title.

Keep these as separate attributes:
- formal plan designation / plan number, where present
- plan name
- property designation(s)
- source title
- aliases and historical names

A title such as “Förslag till ny detaljplan för del av Hertsön 11:1 m fl” and a descriptive subtitle such as “Utveckling av industriområde, Hertsöfältet, KLF2023/1308” should be retained as source evidence. The work ID should be extracted independently from the title/subtitle and not confused with the plan designation or the human-readable plan name.

### 3. Protocol decision reference — event-level supporting key

Example: `2023-10-23 (§ 21)`.

This reference identifies a decision in a particular meeting/protocol context. Store it as a decision-event reference, not as the primary plan/work identifier:
- meeting/decision date: `2023-10-23`
- paragraph/item: `21`
- source protocol or meeting body, when available
- decision-making body, e.g. samhällsbyggnadsutskottet
- exact source wording and provenance

The date and paragraph should remain separate structured values as well as preserving the raw citation. The same paragraph number can occur in many meetings; a date and paragraph without the meeting body/protocol context is not globally unique.

A protocol citation can corroborate that a notice refers to a particular decision, and can anchor an event such as a planning assignment, consultation decision, adoption, or other procedural milestone. Do not infer the event type from the citation alone; use the surrounding decision text or protocol content.

### 4. Other source references — separate namespaces

Keep Kungjort `case_id`, diarienummer, normalized diarienummer, section references, decision IDs and section IDs in separate typed namespaces. Do not merge them into the work-ID field, and do not assume that a generic section/decision identifier is equivalent to the municipal planning work ID.

## Matching policy

Use this evidence order for candidate generation:

1. Exact work ID + same issuing municipality/authority: strongest candidate link.
2. Exact work ID + compatible plan name/property designation: strengthened candidate link.
3. Exact work ID repeated across different procedural notices: link notices to the same matter candidate, then assess process instance and event separately.
4. Protocol date + paragraph + decision-making body + matching plan/work ID: strong support for a particular event.
5. Matching plan designation/name/property references without work ID: candidate only; require corroboration.
6. Similar title, shared municipality, generic plan words or geographic proximity alone: insufficient.

A work ID groups the administrative matter; it does not collapse the matter's history into one event or one proposal version. For example, a matter can have an initial consultation, a revised proposal, a second consultation, review, adoption and legal force. Preserve each notice and event. Create a new process instance when evidence supports a materially revised proposal or a new procedural round.

## Recommended data model additions

For a matter:
- `work_ids[]` with raw/normalized value, authority, validity period and provenance
- `plan_designations[]`
- `plan_names[]` and aliases
- `property_designations[]`

For an event:
- `decision_reference_raw`
- `decision_date`
- `protocol_paragraph`
- `decision_body`
- `protocol_source_reference`
- `event_type` and evidence/provenance

For every candidate relationship:
- source and target notice/matter identifiers (private)
- reference namespace and exact match basis
- authority/jurisdiction check
- supporting and conflicting evidence
- candidate relation type
- confidence / review status
- reason the candidate was generated

## Privacy and processing

Document-level work IDs, protocol references, plan titles and source text remain in private Azure storage. GitHub Actions artifacts and repository reports must contain aggregate counts only. Never publish raw work IDs, protocol citations, titles, municipality-level document rows, or candidate pairs in public repository artifacts.

The first implementation should be read-only and produce private candidate links. It must not update source records, overwrite the immutable selection index, create final matter assignments, or merge process instances automatically.

## Example interpretation

Source wording:

> Förslag till ny Detaljplan för del av Hertsön 11:1 m fl  
> Utveckling av industriområde, Hertsöfältet, KLF2023/1308  
> Samhällsbyggnadsutskottet har beslutat 2023-10-23 (§ 21)

Interpretation:
- plan subject/title: “Förslag till ny Detaljplan för del av Hertsön 11:1 m fl”
- descriptive plan/project name: “Utveckling av industriområde, Hertsöfältet”
- primary work ID: `KLF2023/1308`
- decision-making body: samhällsbyggnadsutskottet
- decision date: `2023-10-23`
- protocol paragraph: `21`
- protocol citation: `2023-10-23 (§ 21)`

The work ID is the primary cross-notice matter reference. The protocol citation is evidence for a dated decision event. Neither should replace the immutable Kungjort notice ID.
