from django.test import TestCase
from fast_grow.models import Ligand


class LigandModelTests(TestCase):
    """Ligand model tests"""

    def test_write_temp(self):
        """Test ligand tempfile is actually wriiten with the correct content and suffix"""
        ligand_string = 'test string'
        ligand = Ligand(name='test', file_type='sdf', file_string=ligand_string)
        ligand_file = ligand.write_temp()
        self.assertIn(ligand.name, ligand_file.name)
        self.assertEqual(ligand_file.name[-3:], ligand.file_type)
        self.assertEqual(ligand_file.read(), ligand_string)
