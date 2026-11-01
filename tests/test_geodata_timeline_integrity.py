import unittest
import numpy as np
from scripts.geodata_timeline import compare_arrays

class TestTimelineIntegrity(unittest.TestCase):
    def test_identical_arrays_have_zero_changed_pixels(self):
        a = np.arange(16, dtype=np.uint8).reshape(4, 4)
        result = compare_arrays(a, a.copy(), [0, 0, 4, 4])
        self.assertEqual(result['comparison_status'], 'compared')
        self.assertEqual(result['bands'][0]['changed_pixel_count'], 0)

    def test_changed_pixels_are_counted_per_band(self):
        a = np.zeros((3, 3, 2), dtype=np.uint8)
        b = a.copy()
        b[1, 2, 0] = 7
        b[0, 0, 1] = 3
        result = compare_arrays(b, a, [100, 200, 103, 203])
        self.assertEqual([x['changed_pixel_count'] for x in result['bands']], [1, 1])
        self.assertEqual([x['changed_percent'] for x in result['bands']], [11.111111, 11.111111])

    def test_shape_mismatch_is_not_compared(self):
        a = np.zeros((3, 3), dtype=np.uint8)
        b = np.zeros((4, 3), dtype=np.uint8)
        result = compare_arrays(a, b, [0, 0, 3, 4])
        self.assertEqual(result['comparison_status'], 'incomparable_shape')

if __name__ == '__main__':
    unittest.main()
