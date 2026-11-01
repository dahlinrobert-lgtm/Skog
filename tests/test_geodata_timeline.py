import unittest
import numpy as np
from scripts.geodata_timeline import pixel_hash, meta_subset, compare_arrays, band_arrays

class TestTimeline(unittest.TestCase):
 def test_same_pixels_same_hash(self):
  a=np.arange(16,dtype=np.uint8).reshape(4,4); self.assertEqual(pixel_hash(a),pixel_hash(a.copy()))
 def test_changed_pixel_changes_hash(self):
  a=np.zeros((4,4),dtype=np.uint8); b=a.copy(); b[1,1]=1; self.assertNotEqual(pixel_hash(a),pixel_hash(b))
 def test_metadata_allowlist(self):
  x=meta_subset({"name":"a","token":"secret","fullExtent":{"spatialReference":{"wkid":3006}}})
  self.assertEqual(x["wkid"],3006); self.assertNotIn("token",x)
 def test_band_level_counts_percent_and_bbox(self):
  old=np.zeros((4,4,2),dtype=np.uint8); new=old.copy()
  new[1,2,0]=3; new[2,1,1]=5
  result=compare_arrays(new,old,[100,200,104,204])
  self.assertEqual(result["comparison_status"],"compared")
  self.assertEqual(result["bands"][0]["changed_pixel_count"],1)
  self.assertEqual(result["bands"][1]["changed_percent"],6.25)
  self.assertEqual(result["bands"][0]["changed_bbox_epsg3006"],{"xmin":102.0,"xmax":103.0,"ymin":202.0,"ymax":203.0})
 def test_nodata_values_are_excluded_from_change_counts(self):
  old=np.array([[[255,1],[2,2]]],dtype=np.uint8)
  new=np.array([[[0,1],[3,2]]],dtype=np.uint8)
  md={"no_data_values":[255,None]}
  result=compare_arrays(new,old,[0,0,2,1],md,md)
  self.assertEqual(result["bands"][0]["valid_pixel_count"],2)
  self.assertEqual(result["bands"][0]["changed_pixel_count"],1)
 def test_shape_change_is_not_compared_as_pixel_change(self):
  result=compare_arrays(np.zeros((3,3)),np.zeros((4,4)),[0,0,4,4])
  self.assertEqual(result["comparison_status"],"incomparable_shape")
 def test_single_band_is_normalized(self):
  self.assertEqual(band_arrays(np.zeros((3,4))).shape,(3,4,1))
if __name__=="__main__": unittest.main()
