"""Tests for conservative Länsstyrelsen diary geographic clue extraction."""
from lansstyrelsen_diary_geocoding import extract_geographic_clues, build_report


def make_record(title, municipality="", postort="", diary="Länsstyrelsen i Test län"):
    return {
        "record_key": "test::1-2026",
        "diary_number": "1-2026",
        "diary": diary,
        "title": title,
        "columns": {"Kommun": municipality, "Postort": postort},
    }


def clues(record):
    return record["geocoding"]["clues"]


def test_extracts_protected_area_and_municipality_from_title():
    result = extract_geographic_clues(make_record(
        "Föranmälan om naturvårdsbränning, Värlekärret i naturreservatet Allgunnen, Högsby kommun"
    ))
    values = {(item["type"], item["value"]) for item in clues(result)}
    assert ("protected_area_name", "Allgunnen") in values
    assert ("municipality", "Högsby") in values
    assert result["geocoding"]["confidence"] == "medium"
    assert result["geocoding"]["coordinates"] is None
    assert result["geocoding"]["circle_radius_m"] is None


def test_extracts_multiple_named_reserves_from_title():
    result = extract_geographic_clues(make_record(
        "Information om planerad naturvårdsbränning i Kynnefjäll och Kroppefjäll naturreservat."
    ))
    values = [item["value"] for item in clues(result) if item["type"] == "protected_area_name"]
    assert any("Kynnefjäll" in value for value in values)
    assert any("Kroppefjäll" in value for value in values)


def test_metadata_only_is_low_confidence_and_not_assumed_burn_location():
    result = extract_geographic_clues(make_record(
        "Ansökan om stöd för naturvårdsbränning av ljunghed och gräsmark",
        municipality="Nässjö", postort="Hok"
    ))
    assert result["geocoding"]["confidence"] == "low"
    assert result["geocoding"]["coordinates"] is None
    assert {item["source"] for item in clues(result) if item["type"] == "municipality"} == {"Kommun column"}
    assert any(item["type"] == "postort" and item["value"] == "Hok" for item in clues(result))


def test_generic_title_without_location_remains_unresolved():
    result = extract_geographic_clues(make_record("Naturvårdsbränning - uppföljning"))
    assert result["geocoding"]["confidence"] == "unresolved"


def test_report_counts_records_and_confidence():
    report = build_report({"schema_version": 1, "records": {
        "a": make_record("Naturvårdsbränning - uppföljning"),
        "b": make_record("Anmälan naturvårdsbränning i Fulufjällets nationalpark"),
    }})
    assert report["record_count"] == 2
    assert report["summary"]["unresolved"] == 1
    assert report["summary"]["medium"] == 1
