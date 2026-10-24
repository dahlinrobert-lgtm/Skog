#!/usr/bin/env python3
"""Regression tests for deduplicated polygon-union coverage in analyze_changes."""
import unittest

from shapely.geometry import box
from shapely.ops import unary_union


def unique_coverage_ha(planned, completed):
    """Union overlaps, clip to planned geometry, and return hectares."""
    clipped = [geom.intersection(planned) for geom in completed if geom.intersects(planned)]
    if not clipped:
        return 0.0
    return unary_union(clipped).area / 10000.0


class GeometricUnionCoverageTests(unittest.TestCase):
    def test_overlapping_completed_polygons_are_not_double_counted(self):
        planned = box(0, 0, 100, 100)  # 1 ha
        completed = [box(0, 0, 60, 100), box(40, 0, 100, 100)]
        # Each polygon is 0.6 ha, but their union is exactly the 1 ha plan.
        self.assertAlmostEqual(unique_coverage_ha(planned, completed), 1.0)

    def test_union_is_clipped_to_planned_polygon(self):
        planned = box(0, 0, 100, 100)
        completed = [box(-50, -50, 150, 150)]
        self.assertAlmostEqual(unique_coverage_ha(planned, completed), 1.0)

    def test_disjoint_polygons_sum_without_inflation(self):
        planned = box(0, 0, 100, 100)
        completed = [box(0, 0, 25, 100), box(75, 0, 100, 100)]
        self.assertAlmostEqual(unique_coverage_ha(planned, completed), 0.5)

    def test_no_candidates_has_zero_coverage(self):
        planned = box(0, 0, 100, 100)
        completed = [box(200, 200, 300, 300)]
        self.assertEqual(unique_coverage_ha(planned, completed), 0.0)

    def test_coverage_cannot_exceed_planned_geometry(self):
        planned = box(0, 0, 100, 100)
        completed = [box(-10, -10, 70, 110), box(30, -10, 110, 110)]
        self.assertLessEqual(unique_coverage_ha(planned, completed), planned.area / 10000.0)


if __name__ == "__main__":
    unittest.main()
