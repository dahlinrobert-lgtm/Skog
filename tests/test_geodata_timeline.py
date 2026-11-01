import unittest
import numpy as np
from scripts.geodata_timeline import pixel_hash, meta_subset
class TestTimeline(unittest.TestCase):
 def test_same_pixels_same_hash(self):
  a=np.arange(16,dtype=np.uint8).reshape(4,4); self.assertEqual(pixel_hash(a),pixel_hash(a.copy()))
 def test_changed_pixel_changes_hash(self):
  a=np.zeros((4,4),dtype=np.uint8); b=a.copy(); b[1,1]=1; self.assertNotEqual(pixel_hash(a),pixel_hash(b))
 def test_metadata_allowlist(self):
  x=meta_subset({"name":"a","token":"secret","fullExtent":{"spatialReference":{"wkid":3006}}})
  self.assertEqual(x["wkid"],3006); self.assertNotIn("token",x)
if __name__=="__main__": unittest.main()
