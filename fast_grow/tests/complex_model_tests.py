from django.test import TestCase
from fast_grow.models import Complex


class ComplexModelTests(TestCase):
    """Complex model tests"""

    def test_write_temp(self):
        """Test complex tempfile is actually wriiten with the correct content and suffix"""
        complex_string = 'test string'
        cmplx = Complex(name='test', file_type='pdb', file_string=complex_string)
        complex_file = cmplx.write_temp()
        self.assertIn(cmplx.name, complex_file.name)
        self.assertEqual(complex_file.name[-3:], cmplx.file_type)
        self.assertEqual(complex_file.read(), complex_string)
