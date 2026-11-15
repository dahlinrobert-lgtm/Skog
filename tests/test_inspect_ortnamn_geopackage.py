from scripts.inspect_ortnamn_geopackage import find_name_matches, normalise_name


def test_normalise_name_handles_case_and_whitespace():
    assert normalise_name("  SÖDRA   Sunderbyn ") == "södra sunderbyn"


def test_find_name_matches_finds_sunderbyn_in_qualified_name():
    hits = find_name_matches(
        {"namn": "Södra Sunderbyn", "typ": "Tätort"},
        ["Sunderbyn", "Notviken"],
    )
    assert hits == [{"target": "Sunderbyn", "field": "namn", "value": "Södra Sunderbyn"}]


def test_find_name_matches_keeps_each_matching_field():
    hits = find_name_matches(
        {"namn": "Notviken", "alternativnamn": "Notviken"},
        ["Notviken"],
    )
    assert [hit["field"] for hit in hits] == ["namn", "alternativnamn"]


def test_find_name_matches_does_not_match_empty_values():
    assert find_name_matches({"namn": None, "typ": ""}, ["Sunderbyn"]) == []
