"""Celery task tests"""
import os
import subprocess
from django.test import TestCase
from fast_grow.models import Complex, Core, Growing, Ligand, Status
from fast_grow.tasks import preprocess_complex, clip_ligand, grow
from fast_grow.settings import PREPROCESSOR, CLIPPER, FAST_GROW
from .fixtures import TEST_FILES, create_test_complex, create_test_ligand, create_test_growing


class TaskTests(TestCase):
    """Celery task tests"""

    def test_preprocessor_available(self):
        """Test the preprocessor binary exists at the correct location and is licensed"""
        self.assertTrue(
            os.path.exists(PREPROCESSOR),
            'Preprocessor binary does not exist at {}'.format(PREPROCESSOR)
        )
        completed_process = subprocess.run(
            PREPROCESSOR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
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
            name='4agm', file_type='pdb', file_string=complex_string)
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
        self.assertTrue(
            os.path.exists(CLIPPER), 'Clipper binary does not exist at {}'.format(CLIPPER))
        completed_process = subprocess.run(
            CLIPPER, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
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

    def test_fast_grow_available(self):
        """Test the fast grow binary exists and is licensed"""
        self.assertTrue(
            os.path.exists(FAST_GROW), 'Fast Grow binary does not exist at {}'.format(FAST_GROW))
        completed_process = subprocess.run(
            FAST_GROW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        # 64 == ArgumentError, which means the preprocessor is ready to accept arguments
        self.assertEqual(completed_process.returncode, 64,
                         'Fast Grow ran with unexpected error code. Is it licensed?')

    def test_growing(self):
        """Test fast grow processes a growing"""
        growing = create_test_growing()
        try:
            grow.run(growing.id)
        finally:
            subprocess.check_call(['dropdb', growing.fragment_set.name])
        growing = Growing.objects.get(id=growing.id)
        self.assertEqual(growing.hit_set.count(), 11)
        growing_dict = growing.dict(detail=True)
        self.assertEqual(growing_dict['status'], 'success')
        self.assertEqual(
            growing_dict['hits'],
            sorted(growing_dict['hits'], key=lambda x: x['score'])
        )

    def test_growing_with_search_points(self):
        """Test fast grow processes a growing with search points"""
        growing = create_test_growing(search_points=True)
        try:
            grow.run(growing.id)
        finally:
            subprocess.check_call(['dropdb', growing.fragment_set.name])
        growing = Growing.objects.get(id=growing.id)
        # fewer hits due to search point filtering
        self.assertEqual(growing.hit_set.count(), 6)
        growing_dict = growing.dict()
        self.assertEqual(growing_dict['status'], 'success')

    # def test_growing_with_ensemble(self):
    #     """Test fast grow processes a growing using an ensemble"""
    #     growing = create_test_growing(use_ensemble=True)
    #     try:
    #         grow.run(growing.id)
    #     finally:
    #         subprocess.check_call(['dropdb', growing.fragment_set.name])
    #     growing = Growing.objects.get(id=growing.id)
    #     print(growing.ensemble.dict())
    #     self.assertEqual(growing.hit_set.count(), 11)
    #     growing_dict = growing.dict()
    #     self.assertEqual(growing_dict['status'], 'success')

    def test_growing_fail(self):
        """Test fast grow processes a growing"""
        growing = create_test_growing()
        growing.fragment_set.name = 'fake'
        growing.fragment_set.save()
        try:
            grow.run(growing.id)
        except Exception:
            growing = Growing.objects.get(id=growing.id)
            self.assertEqual(growing.status, Status.FAILURE)
        finally:
            subprocess.check_call(['dropdb', 'test_fragment_set'])
