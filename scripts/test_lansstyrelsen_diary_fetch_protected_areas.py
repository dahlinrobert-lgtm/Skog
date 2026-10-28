"""Tests for the official protected-area ZIP/shapefile fetcher."""
import io
import tempfile
import zipfile
from pathlib import Path

import shapefile
from pyproj import CRS

from lansstyrelsen_diary_fetch_protected_areas import candidate_names, is_candidate_name, parse_archive


def sample_zip():
    shp_buf, shx_buf, dbf_buf = io.BytesIO(), io.BytesIO(), io.BytesIO()
    writer = shapefile.Writer(shp=shp_buf, shx=shx_buf, dbf=dbf_buf, shapeType=shapefile.POLYGON)
    writer.field("NAMN", "C", size=80)
    writer.field("NVRID", "C", size=20)
    writer.poly([[[500000, 6400000], [500100, 6400000], [500100, 6400100], [500000, 6400100], [500000, 6400000]]])
    writer.record("Allgunnen", "NVR-1")
    writer.poly([[[500200, 6400200], [500300, 6400200], [500300, 6400300], [500200, 6400300], [500200, 6400200]]])
    writer.record("Some other reserve", "NVR-2")
    writer.close()
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp) / "protected"
        base.with_suffix(".shp").write_bytes(shp_buf.getvalue())
        base.with_suffix(".shx").write_bytes(shx_buf.getvalue())
        base.with_suffix(".dbf").write_bytes(dbf_buf.getvalue())
        base.with_suffix(".prj").write_text(CRS.from_epsg(3006).to_wkt(), encoding="utf-8")
        base.with_suffix(".cpg").write_text("UTF-8", encoding="ascii")
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in Path(temp).iterdir():
                archive.write(path, path.name)
        return out.getvalue()


def test_candidate_name_normalization_and_swedish_genitive():
    wanted = candidate_names({"features": [{"geocoding": {"clues": [
        {"type": "protected_area_name", "value": "Fulufjällets nationalpark"},
        {"type": "municipality", "value": "Högsby"},
    ]}}]})
    assert "fulufjallets" in wanted
    assert is_candidate_name("Fulufjället", wanted)
    assert not is_candidate_name("Högsby", wanted)


def test_parses_official_shapefile_filters_unrelated_features_and_transforms_crs():
    features, source_count = parse_archive(sample_zip(), "NR", {"allgunnen"})
    assert source_count == 2
    assert len(features) == 1
    assert features[0]["properties"]["NAMN"] == "Allgunnen"
    assert features[0]["properties"]["SOURCE_DATASET"] == "NR"
    x, y = features[0]["geometry"]["coordinates"][0][0]
    assert 10 <= x <= 25
    assert 54 <= y <= 70
