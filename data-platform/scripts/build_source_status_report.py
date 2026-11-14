#!/usr/bin/env python3
"""Build a deterministic Markdown status report from the Skog source registry."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "data-platform" / "config" / "sources.yml"
DEFAULT_OUTPUT = ROOT / "docs" / "SKOGSKOLL_SOURCE_STATUS.md"

LABELS = {
    "access_status": {
        "verified": "Verifierad",
        "partial": "Delvis verifierad",
        "technical_probe": "Teknisk probe",
        "authorised_access_used": "Auktoriserad åtkomst använd",
        "not_verified": "Ej verifierad",
        "planned": "Planerad",
    },
    "snapshot_status": {
        "recurring": "Återkommande",
        "pilot": "Pilot",
        "partial": "Delvis",
        "baseline_only": "Endast baslinje",
        "not_started": "Inte startad",
        "metadata_monitoring_needs_repair": "Metadatabevakning behöver repareras",
        "pilot_for_selected_layers": "Pilot för utvalda lager",
        "monthly_archive_planned_or_pilot": "Månadsarkiv planerat/pilot",
        "30_day_daily_observation_test": "30-dagars dagligt test",
    },
    "history_status": {
        "time_series": "Tidsserie",
        "partial": "Delvis historik",
        "metadata_series_only": "Endast metadataserie",
        "not_verified": "Ej verifierad",
        "none": "Ingen",
        "historical_archive_partial": "Delvis historiskt arkiv",
    },
    "commercial_use_status": {
        "verified": "Verifierad",
        "verified_with_attribution": "Verifierad med källhänvisning",
        "conditional": "Villkorad",
        "conditional_on_attribution_and_source_scope": "Villkorad av attribution/källomfattning",
        "conditional_per_product": "Villkorad per produkt",
        "conditional_per_record": "Villkorad per handling/post",
        "pending_product_terms": "Inväntar produktvillkor",
        "pending_scope_confirmation": "Inväntar omfattningsbesked",
        "restricted": "Begränsad",
        "unknown": "Okänd",
    },
    "customer_display_status": {
        "approved": "Godkänd",
        "conditional": "Villkorad",
        "conditional_on_attribution_and_source_scope": "Villkorad av attribution/källomfattning",
        "pending_product_layer_check": "Inväntar lagerkontroll",
        "pending_layer_check": "Inväntar lagerkontroll",
        "pending_product_description_check": "Inväntar produktbeskrivning",
        "pending_per_product": "Inväntar produktbedömning",
        "pending_per_document_review": "Inväntar dokumentgranskning",
        "pending_written_or_ordered_scope": "Inväntar skriftligt/beställt scope",
        "pending_scope_confirmation": "Inväntar omfattningsbesked",
        "not_assessed": "Ej bedömd",
    },
}

FIELDS = (
    ("access_status", "Åtkomst"),
    ("snapshot_status", "Snapshots"),
    ("history_status", "Historik"),
    ("commercial_use_status", "Kommersiellt"),
    ("customer_display_status", "Kundvisning"),
)


def md(value: Any) -> str:
    if value is None or value == "":
        return "—"
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def label(field: str, value: Any) -> str:
    if value is None:
        return "Ej bedömd"
    return LABELS.get(field, {}).get(str(value), str(value))


def build_report(data: dict[str, Any]) -> str:
    sources = data["sources"]
    operational = [s for s in sources if isinstance(s.get("operations"), dict)]
    unassessed = len(sources) - len(operational)
    lines = [
        "# Skogskoll – automatisk status för datakällor",
        "",
        f"**Register kontrollerat:** {md(data.get('registry_checked_on', 'Ej angivet'))}  ",
        f"**Rapport genererad:** {date.today().isoformat()}  ",
        f"**Underlag:** data-platform/config/sources.yml",
        "",
        "> Rapporten är maskinellt sammanställd från källregistret. Den är en operativ översikt, inte ett juridiskt godkännande. Saknat operations-block betyder **inte bedömd**, inte nekad åtkomst eller förbjuden användning.",
        "",
        "## Sammanfattning",
        "",
        f"- Registrerade datakällor: **{len(sources)}**",
        f"- Källor med operativ status: **{len(operational)}**",
        f"- Källor som ännu inte har operativ status: **{unassessed}**",
    ]

    for field, title in FIELDS:
        counts = Counter(label(field, s["operations"].get(field)) for s in operational)
        rendered = ", ".join(f"{name}: {count}" for name, count in sorted(counts.items()))
        lines.append(f"- {title}: {rendered or 'Inga statusvärden'}")

    approved = sum(
        s["operations"].get("customer_display_status") == "approved"
        for s in operational
    )
    lines.extend([
        f"- Uttryckligen godkända för kundvisning i registret: **{approved}**",
        "",
        "## Operativ status per datakälla",
        "",
        "| Datakälla | Käll-ID | Åtkomst | Snapshots | Historik | Kommersiellt | Kundvisning | Senast verifierad |",
        "|---|---|---|---|---|---|---|---|",
    ])

    for source in operational:
        ops = source["operations"]
        cells = [
            md(source.get("name")),
            md(source.get("source_id")),
            label("access_status", ops.get("access_status")),
            label("snapshot_status", ops.get("snapshot_status")),
            label("history_status", ops.get("history_status")),
            label("commercial_use_status", ops.get("commercial_use_status")),
            label("customer_display_status", ops.get("customer_display_status")),
            md(ops.get("last_verified")),
        ]
        lines.append("| " + " | ".join(cells) + " |")

    lines.extend(["", "## Nästa åtgärd", ""])
    for source in operational:
        ops = source["operations"]
        action = ops.get("next_action", "Nästa åtgärd saknas i registret.")
        lines.append(f"- **{md(source.get('name'))}:** {md(action)}")

    lines.extend([
        "",
        "## Tolkning och begränsningar",
        "",
        "- En tekniskt fungerande endpoint/probe visar inte att hela datamängden har hämtats.",
        "- En snapshotserie är inte automatiskt en komplett eller jämförbar historisk tidsserie.",
        "- partial, failed eller annan ofullständig insamling får inte användas för att dra slutsatser om att objekt har försvunnit.",
        "- Kommersiell användning, historisk lagring, bearbetning, kundvisning och vidare distribution ska bedömas separat.",
        "- Statusen approved för kundvisning måste ha konkret produkt-/lagerunderlag och dokumenterad evidens.",
        "- Den här rapporten läser endast registret; den startar inga insamlingsflöden och ändrar inte källstatus.",
        "",
        "## Källor och förvaltning",
        "",
        "- Huvuddokumentation: [SKOGSKOLL_DATA_OVERVIEW.md](SKOGSKOLL_DATA_OVERVIEW.md)",
        "- Rättighetsbedömning: [open-data-and-commercial-use.md](open-data-and-commercial-use.md)",
        "- Källregister: [sources.yml](../data-platform/config/sources.yml)",
        "- Validering: [validate_source_registry.py](../data-platform/scripts/validate_source_registry.py)",
        "- Rapportgenerator: [build_source_status_report.py](../data-platform/scripts/build_source_status_report.py)",
        "",
        "Generera lokalt med:",
        "",
        "    python -m pip install PyYAML==6.0.2",
        "    python data-platform/scripts/build_source_status_report.py --write",
        "",
        "Kontrollera att rapporten är aktuell med:",
        "",
        "    python data-platform/scripts/build_source_status_report.py --check",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="write the generated report")
    group.add_argument("--check", action="store_true", help="fail if the report is stale")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    try:
        data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SystemExit(f"Could not read source registry: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("sources"), list):
        raise SystemExit("Source registry must contain a sources list.")

    generated = build_report(data)
    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(generated, encoding="utf-8")
        print(f"Wrote {args.output}")
        return 0

    try:
        current = args.output.read_text(encoding="utf-8")
    except OSError:
        print(f"Report missing: {args.output}")
        return 1
    if current != generated:
        print(f"Report is stale: {args.output}")
        print("Run: python data-platform/scripts/build_source_status_report.py --write")
        return 1
    print(f"Report is up to date: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
