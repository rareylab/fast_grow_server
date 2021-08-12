"""Core model tests"""
from django.test import TestCase
from fast_grow.models import Core


class CoreModelTests(TestCase):
    """Core model tests"""

    def test_write_temp(self):
        """Test core tempfile is actually written with the correct content and suffix"""
        core_string = 'test string'
        core = Core(name='test', file_type='sdf', file_string=core_string)
        core_file = core.write_temp()
        self.assertIn(core.name, core_file.name)
        self.assertEqual(core_file.name[-3:], core.file_type)
        self.assertEqual(core_file.read(), core_string)
