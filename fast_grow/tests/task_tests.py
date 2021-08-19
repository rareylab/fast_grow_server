"""Celery task tests"""
from datetime import datetime
import os
import subprocess
from django.test import TestCase
from fast_grow_server import settings
from fast_grow.models import Complex, Core, Ligand, Status
from fast_grow.tasks import preprocess_complex, clip_ligand
from fast_grow.settings import PREPROCESSOR, CLIPPER
from .fixtures import TEST_FILES, create_test_complex, create_test_ligand


class TaskTests(TestCase):
    """Celery task tests"""

    def test_preprocessor_available(self):
        """Test the preprocessor binary exists at the correct location and is licensed"""
        path = PREPROCESSOR
        self.assertTrue(
            os.path.exists(path), 'Preprocessor binary does not exist at {}'.format(path))
        completed_process = subprocess.run(
            path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        # 64 == ArgumentError, which means the preprocessor is ready to accept arguments
        self.assertEqual(completed_process.returncode, 64,
                         'Preprocessor ran with unexpected error code. Is it licensed?')

    def test_preprocess_complex(self):
        """Test the preprocessor correctly processes a complex file on it's own"""
        cmplx = create_test_complex()
        preprocess_complex.run(cmplx.id)
        cmplx = Complex.objects.get(id=cmplx.id)
        self.assertEqual(cmplx.status, Status.SUCCESS)
        self.assertEqual(cmplx.ligand_set.count(), 2)
        self.assertEqual(cmplx.searchpointdata_set.count(), 2)

    def test_preprocess_complex_with_ligand(self):
        """Test the preprocessor correctly processes a complex with an explicitly set ligand"""
        cmplx = create_test_complex(custom_ligand=True)
        preprocess_complex.run(cmplx.id)
        cmplx = Complex.objects.get(id=cmplx.id)
        self.assertEqual(cmplx.status, Status.SUCCESS)
        self.assertEqual(cmplx.ligand_set.count(), 1)

    def test_preprocess_fail(self):
        """Test the preprocessor failure states"""
        # complex does not exist
        try:
            preprocess_complex.run(404)
        except Complex.DoesNotExist as error:
            self.assertEqual(str(error), 'Complex matching query does not exist.')

        # complex with two ligands (suggests already processed complex)
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

    def test_clipper_available(self):
        """Test the clipper binary exists at the correct location and is licensed"""
        path = CLIPPER
        self.assertTrue(
            os.path.exists(path), 'Clipper binary does not exist at {}'.format(path))
        completed_process = subprocess.run(
            path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        # 64 == ArgumentError, which means the preprocessor is ready to accept arguments
        self.assertEqual(completed_process.returncode, 64,
                         'Clipper ran with unexpected error code. Is it licensed?')

    def test_clip_ligand(self):
        """Test the clipper clips a ligand into a valid core"""
        ligand = create_test_ligand()
        core = Core(name='P86_A_400_18_2', ligand=ligand, anchor=18, linker=2)
        core.save()

        clip_ligand.run(core.id)
        core = Core.objects.get(id=core.id)
        self.assertEqual(core.status, Status.SUCCESS)
        self.assertIsNotNone(core.file_string)
        self.assertIsNotNone(core.file_type)

    def test_clip_fail(self):
        """Test the clipper fails using invalid anchor or linker positions"""
        ligand = create_test_ligand()
        core = Core(name='P86_A_400_18_2', ligand=ligand, anchor=18, linker=3)
        core.save()
        try:
            clip_ligand.run(core.id)
        except subprocess.CalledProcessError as error:
            self.assertEqual(70, error.returncode)
