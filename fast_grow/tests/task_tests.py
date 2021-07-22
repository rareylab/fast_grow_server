from datetime import datetime
import os
import subprocess
from django.test import TestCase
from fast_grow_server import settings
from fast_grow.models import Complex, Ligand, Status
from fast_grow.tasks import preprocess_complex

TEST_FILES = os.path.join(settings.BASE_DIR, 'fast_grow', 'tests', 'test_files')


class TaskTests(TestCase):
    """Celery task tests"""

    def test_preprocessor_available(self):
        """Test the preprocessor binary exists at the correct location and is licensed"""
        path = os.path.join(settings.BASE_DIR, 'bin', 'preprocessor')
        self.assertTrue(
            os.path.exists(path), 'Preprocessor binary does not exist at {}'.format(path))
        completed_process = subprocess.run(
            path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        # 64 == ArgumentError, which means the preprocessor is ready to accept arguments
        self.assertEqual(completed_process.returncode, 64,
                         'Preprocessor ran with unexpected error code. Is it licensed?')

    def test_preprocess_complex(self):
        """Test the preprocessor correctly processes a complex file on it's own"""
        with open(os.path.join(TEST_FILES, '4agm.pdb')) as complex_file:
            complex_string = complex_file.read()
        cmplx = Complex(
            name='4agm', file_type='pdb', file_string=complex_string, accessed=datetime.now())
        cmplx.save()

        preprocess_complex.run(cmplx.id)
        cmplx = Complex.objects.get(id=cmplx.id)
        self.assertEqual(cmplx.status, Status.SUCCESS)
        self.assertEqual(cmplx.ligand_set.count(), 2)
        self.assertEqual(cmplx.searchpointdata_set.count(), 2)

    def test_preprocess_complex_with_ligand(self):
        """Test the preprocessor correctly processes a complex with an explicitly set ligand"""
        with open(os.path.join(TEST_FILES, '4agm.pdb')) as complex_file:
            complex_string = complex_file.read()
        cmplx = Complex(
            name='4agm', file_type='pdb', file_string=complex_string, accessed=datetime.now())
        cmplx.save()

        with open(os.path.join(TEST_FILES, 'P86_A_400.sdf')) as ligand_file:
            ligand_string = ligand_file.read()
        ligand = Ligand(
            name='P86_A_400', file_type='sdf', file_string=ligand_string, complex=cmplx)
        ligand.save()

        preprocess_complex.run(cmplx.id)
        cmplx = Complex.objects.get(id=cmplx.id)
        self.assertEqual(cmplx.status, Status.SUCCESS)
        self.assertEqual(cmplx.ligand_set.count(), 1)
        # self.assertEqual(cmplx.interaction_set.count(), 26)
        # self.assertEqual(cmplx.interaction_set.filter(water_interaction=True).count(), 12)

    def test_preprocess_fail(self):
        try:
            preprocess_complex.run(404)
        except Complex.DoesNotExist as error:
            self.assertEqual(str(error), 'Complex matching query does not exist.')

        with open(os.path.join(TEST_FILES, '4agm.pdb')) as complex_file:
            complex_string = complex_file.read()
        cmplx = Complex(
            name='4agm', file_type='pdb', file_string=complex_string, accessed=datetime.now())
        cmplx.save()

        with open(os.path.join(TEST_FILES, 'P86_A_400.sdf')) as ligand_file:
            ligand_string = ligand_file.read()
        ligand = Ligand(
            name='P86_A_400', file_type='sdf', file_string=ligand_string, complex=cmplx)
        ligand.save()
        ligand = Ligand(
            name='P86_A_400', file_type='sdf', file_string=ligand_string, complex=cmplx)
        ligand.save()
        try:
            preprocess_complex.run(cmplx.id)
        except Exception as error:
            self.assertEqual(str(error),
                             'complex({}) to be processed has more than one ligand'.format(
                                 cmplx.id))
