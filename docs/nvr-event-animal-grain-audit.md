# NVR event- and animal-level structure: Luleå pilot audit

## Purpose

Document the distinction between an NVR collision event and the individual animal records attached to it. This distinction is required when comparing NVR data with Police wildlife-collision statements: one Police incident may involve several animals, while NVR may represent those animals as several rows belonging to one collision event.

This is a structural audit of the local historical NVR export, not a validation of individual Police–NVR matches. No row-level NVR or Police data is committed by this document.

## Data grain and identifiers

The historical NVR export is animal-level: each source row represents an animal record and includes fields such as `DjurID`, `OlycksID`, `Datum`, `Kommun`, `Viltslag`, coordinates and `Vad har skett med viltet`.

Use a year-qualified event key, `year + OlycksID`, when grouping animal rows into collision events. Do not use raw `OlycksID` alone: the same ID value occurs in more than one year in the inspected historical material.

Keep the two grains explicit:
- **Event grain:** one collision event, identified provisionally by year-qualified `OlycksID`.
- **Animal grain:** one animal record, identified by `DjurID` only after global uniqueness has been checked.

Do not count each animal row as a separate collision. Preserve the animal rows and their outcomes underneath the event-level record.

## Luleå historical pilot audit

A Unicode-normalized municipality filter was applied to the annual source CSV files. The local audit reported:

| Measure | Result |
|---|---:|
| Animal-level records in Luleå | 1,745 |
| Events with more than one animal record | 31 |
| Multi-animal events with differing animal outcomes | 8 |
| Multi-animal events with more than one distinct WGS84 coordinate | 0 |
| Multi-animal events with repeated `DjurID` within the event | 0 |

The 31 multi-animal events therefore demonstrate why animal-row counts and event counts must not be conflated. The eight mixed-outcome events also show that one event can contain animals with different reported outcomes, for example an animal assessed unharmed alongside an animal recorded as euthanized or found dead.

In this Luleå sample, all animal rows within each of the 31 multi-animal events shared one distinct WGS84 coordinate. This is an observed property of this sample only. It does **not** establish whether the coordinate always represents the original collision location, the search/recovery location, or another operationally recorded location. Do not infer an animal's individual position or the location/time of a later search or euthanasia from this coordinate or from the outcome text.

## Implications for Police–NVR matching

1. Generate Police–NVR candidates at event grain, not by independently matching every animal row.
2. Retain the linked animal records as event detail so that multiple animals and mixed outcomes remain visible to reviewers.
3. Permit a Police incident to correspond to one NVR event containing several animal rows. Do not turn those animal rows into multiple Police collision matches.
4. Keep event-level time and location evidence separate from animal-level species and outcome evidence. Where animal rows contain differing values, preserve all values and document the aggregation rule.
5. Keep candidate links review-only. This audit does not establish any individual Police–NVR match.

## Limitations and outstanding checks

- The audit covers the local Luleå subset and does not prove that the same multi-animal patterns hold nationally.
- Global uniqueness of `DjurID` across all years and the complete national export has **not yet been verified**. Until that check is complete, treat `DjurID` as a source identifier, not as a proven globally unique primary key.
- Year-qualified `OlycksID` is the event grouping key used by the current workflow; validate it against the full national history before treating it as a permanent source contract.
- The export does not provide explicit separate timestamps or coordinates for the original collision, search, recovery, or euthanasia in the fields inspected. Outcome categories such as `Avlivat` and `Påträffat dött` are not timestamps or independent locations.
- Identical coordinates across animal rows do not resolve the semantic meaning or positional accuracy of the coordinate.

## Next validation steps

1. Check `DjurID` uniqueness across the complete national 2015–2026 animal-level export, including missing and repeated identifiers.
2. Validate the year-qualified event key nationally and quantify multi-animal events and mixed outcomes by year, municipality and species.
3. Preserve a normalized event table plus a child animal table; never discard animal-level detail during event aggregation.
4. If the source later supplies separate collision and search/recovery details, model them as distinct observations with their own timestamps, locations and provenance.
5. Add automated tests that prove multi-animal rows aggregate to one event while all animal rows and outcomes remain accessible.

## Reproducibility note

The figures above are transcribed from the local Luleå audit performed on the historical annual CSV splits. The source files are stored outside this repository. No personal, row-level, or restricted source records are included here. Re-run the audit against the controlled source archive before using these counts as a national or production-wide quality statement.
