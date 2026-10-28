"""Tests for authoritative protected-area name matching."""
import json

from lansstyrelsen_diary_protected_area_match import match_candidate, normalize, split_candidate


def feature(name, geometry=None, nvrid="NVR-1"):
    return {"type": "Feature", "properties": {"NAMN": name, "NVRID": nvrid}, "geometry": geometry}


def candidate(name, clue_type="protected_area_name"):
    return {
        "diary_number": "1-2026", "title": "Anmälan naturvårdsbränning",
        "geocoding": {"confidence": "medium", "clues": [{"type": clue_type, "value": name, "source": "title"}]},
    }


def test_normalization_handles_swedish_diacritics_and_case():
    assert normalize("Kärnskogsmossens") == normalize("KARNSKOGSMOSSENS")


def test_split_two_area_names():
    assert split_candidate("Kynnefjäll och Kroppefjäll naturreservat") == ["Kynnefjäll", "Kroppefjäll"]


def test_unique_exact_match_gets_polygon_circle_and_popup():
    polygon = {
        "type": "Polygon",
        "coordinates": [[[14.0, 58.0], [14.01, 58.0], [14.01, 58.01], [14.0, 58.01], [14.0, 58.0]]],
    }
    result = match_candidate(candidate("Allgunnen"), [feature("Allgunnen", polygon)], ["NAMN"])
    geo = result["geocoding"]
    assert geo["status"] == "matched_official_protected_area"
    assert geo["coordinates"]["latitude"] is not None
    assert geo["circle_radius_m"] > 0
    assert geo["geometry"]["type"] == "Polygon"
    assert "does not claim" in geo["popup"]["circle_explanation"]


def test_ambiguous_match_does_not_assign_coordinates():
    features = [feature("Allgunnen", {"type": "Polygon", "coordinates": [[[14,58],[14.01,58],[14.01,58.01],[14,58.01],[14,58]]]}, "A"),
                feature("Allgunnen", {"type": "Polygon", "coordinates": [[[15,58],[15.01,58],[15.01,58.01],[15,58.01],[15,58]]]}, "B")]
    result = match_candidate(candidate("Allgunnen"), features, ["NAMN"])
    assert result["geocoding"]["status"] == "ambiguous_official_matches"
    assert result["geocoding"]["coordinates"] is None


def test_no_match_stays_ungeocoded():
    result = match_candidate(candidate("NoSuchReserve"), [feature("Allgunnen")], ["NAMN"])
    assert result["geocoding"]["status"] == "no_official_protected_area_match"
    assert result["geocoding"]["coordinates"] is None


def test_municipality_only_clue_is_not_used_as_protected_area_match():
    result = match_candidate(candidate("Högsby", "municipality"), [feature("Högsby")], ["NAMN"])
    assert result["geocoding"]["coordinates"] is None
    assert result["geocoding"]["status"] == "no_official_protected_area_match"
