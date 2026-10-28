"""Tests for the official protected-area WFS fetcher."""
import json

import pytest

from lansstyrelsen_diary_fetch_protected_areas import fetch_all


def test_paginates_and_deduplicates(monkeypatch):
    responses = [
        {"features": [{"id": "x.1", "properties": {}, "geometry": {}}, {"id": "x.2", "properties": {}, "geometry": {}}]},
        {"features": [{"id": "x.2", "properties": {}, "geometry": {}}, {"id": "x.3", "properties": {}, "geometry": {}}]},
        {"features": []},
    ]
    calls = []
    def fake(url, timeout=90):
        calls.append(url)
        return responses[len(calls)-1]
    monkeypatch.setattr("lansstyrelsen_diary_fetch_protected_areas.request_json", fake)
    result = fetch_all(page_size=2, max_features=10)
    assert len(calls) == 3
    assert [f["id"] for f in result["features"]] == ["x.1", "x.2", "x.3"]


def test_stops_on_short_page(monkeypatch):
    monkeypatch.setattr("lansstyrelsen_diary_fetch_protected_areas.request_json", lambda url, timeout=90: {"features": [{"id": "only.1"}]})
    assert len(fetch_all(page_size=2)["features"]) == 1


def test_empty_dataset_fails_closed(monkeypatch):
    monkeypatch.setattr("lansstyrelsen_diary_fetch_protected_areas.request_json", lambda url, timeout=90: {"features": []})
    with pytest.raises(RuntimeError):
        fetch_all(page_size=2)
