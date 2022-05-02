"""Tests for the growing model"""
import subprocess
from django.test import TestCase
from .fixtures import processed_ensemble_search_point_growing, delete_test_fragment_set


class GrowingModelTests(TestCase):
    """Tests for the growing model"""

    def test_write_zip(self):
        """Test whether the growing can be written as zip bytes"""
        growing = processed_ensemble_search_point_growing()
        try:
            zip_bytes = growing.write_zip_bytes()
            zip_contents = zip_bytes.getvalue()
            self.assertIn(bytes('growing/ensemble/4agn.pdb', encoding='utf8'), zip_contents)
            self.assertIn(bytes('growing/ensemble/4agm.pdb', encoding='utf8'), zip_contents)
            self.assertIn(bytes('growing/search_points.json', encoding='utf8'), zip_contents)
            self.assertIn(bytes('growing/P86_A_400_18_2.sdf', encoding='utf8'), zip_contents)
            self.assertIn(bytes('growing/hits.sdf', encoding='utf8'), zip_contents)
        finally:
            delete_test_fragment_set(growing.fragment_set.name)
