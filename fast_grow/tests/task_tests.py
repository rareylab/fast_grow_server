"""Celery task tests"""
import os
import subprocess
from django.test import TestCase
from fast_grow.models import Complex, Core, Growing, Ligand, SearchPointData, Status, Ensemble
from fast_grow.tasks import preprocess_ensemble, clip_ligand, grow, generate_interactions
from fast_grow.settings import PREPROCESSOR, CLIPPER, INTERACTIONS, FAST_GROW
from .fixtures import TEST_FILES, multi_ensemble, single_ensemble, single_ensemble_with_ligand, \
    test_ligand, test_growing, search_point_growing, ensemble_growing, delete_test_fragment_set


class TaskTests(TestCase):
    """Celery task tests"""

    def test_preprocessor_available(self):
        """Test the preprocessor binary exists at the correct location and is licensed"""
        self.assertTrue(
            os.path.exists(PREPROCESSOR),
            f'Preprocessor binary does not exist at {PREPROCESSOR}'
        )
        completed_process = subprocess.run(
            PREPROCESSOR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        # 64 == ArgumentError, which means the preprocessor is ready to accept arguments
        self.assertEqual(completed_process.returncode, 64,
                         'Preprocessor ran with unexpected error code. Is it licensed?')

    def test_preprocess_ensemble(self):
        """Test the preprocessor correctly processes an ensemble"""
        ensemble = multi_ensemble()
        preprocess_ensemble.run(ensemble.id)
        ensemble = Ensemble.objects.get(id=ensemble.id)
        self.assertEqual(ensemble.status, Status.SUCCESS)
        self.assertEqual(ensemble.complex_set.count(), 2)
        self.assertEqual(ensemble.ligand_set.count(), 1)

    def test_preprocess_single_ensemble(self):
        """Test the preprocessor correctly processes a complex file on it's own"""
        ensemble = single_ensemble()
        preprocess_ensemble.run(ensemble.id)
        ensemble = Ensemble.objects.get(id=ensemble.id)
        self.assertEqual(ensemble.status, Status.SUCCESS)
        self.assertEqual(ensemble.complex_set.count(), 1)
        self.assertEqual(ensemble.ligand_set.count(), 2)

    def test_preprocess_complex_with_ligand(self):
        """Test the preprocessor correctly processes a complex with an explicitly set ligand"""
        ensemble = single_ensemble_with_ligand()
        preprocess_ensemble.run(ensemble.id)
        ensemble = Ensemble.objects.get(id=ensemble.id)
        self.assertEqual(ensemble.status, Status.SUCCESS)
        self.assertEqual(ensemble.complex_set.count(), 1)
        self.assertEqual(ensemble.ligand_set.count(), 1)

    def test_preprocess_fail(self):
        """Test the preprocessor failure states"""
        # complex does not exist
        try:
            preprocess_ensemble.run(404)
        except Ensemble.DoesNotExist as error:
            self.assertEqual(str(error), 'Ensemble matching query does not exist.')

        ensemble = Ensemble()
        ensemble.save()
        # complex with two ligands (suggests already processed complex)
        with open(os.path.join(TEST_FILES, '4agm.pdb'), encoding='utf8') as complex_file:
            complex_string = complex_file.read()
        cmplx = Complex(
            ensemble=ensemble, name='4agm', file_type='pdb', file_string=complex_string)
        cmplx.save()

        with open(os.path.join(TEST_FILES, 'P86_A_400.sdf'), encoding='utf8') as ligand_file:
            ligand_string = ligand_file.read()
        ligand = Ligand(
            ensemble=ensemble, name='P86_A_400', file_type='sdf', file_string=ligand_string)
        ligand.save()
        ligand = Ligand(
            ensemble=ensemble, name='P86_A_400', file_type='sdf', file_string=ligand_string)
        ligand.save()
        with self.assertRaises(RuntimeError):
            preprocess_ensemble.run(ensemble.id)

    def test_clipper_available(self):
        """Test the clipper binary exists at the correct location and is licensed"""
        self.assertTrue(
            os.path.exists(CLIPPER), f'Clipper binary does not exist at {CLIPPER}')
        completed_process = subprocess.run(
            CLIPPER, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        # 64 == ArgumentError, which means the preprocessor is ready to accept arguments
        self.assertEqual(completed_process.returncode, 64,
                         'Clipper ran with unexpected error code. Is it licensed?')

    def test_clip_ligand(self):
        """Test the clipper clips a ligand into a valid core"""
        ligand = test_ligand()
        core = Core(name='P86_A_400_18_2', ligand=ligand, anchor=18, linker=2)
        core.save()

        clip_ligand.run(core.id)
        core = Core.objects.get(id=core.id)
        self.assertEqual(core.status, Status.SUCCESS)
        self.assertIsNotNone(core.file_string)
        self.assertIsNotNone(core.file_type)

    def test_clip_fail(self):
        """Test the clipper fails using invalid anchor or linker positions"""
        ligand = test_ligand()
        core = Core(name='P86_A_400_18_2', ligand=ligand, anchor=18, linker=3)
        core.save()
        try:
            clip_ligand.run(core.id)
        except subprocess.CalledProcessError as error:
            self.assertEqual(70, error.returncode)

    def test_interactions_available(self):
        """Test the clipper binary exists at the correct location and is licensed"""
        self.assertTrue(os.path.exists(INTERACTIONS),
                        f'Interaction generator binary does not exist at {CLIPPER}')
        completed_process = subprocess.run(
            INTERACTIONS, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        # 64 == ArgumentError, which means the preprocessor is ready to accept arguments
        self.assertEqual(completed_process.returncode, 64,
                         'Interaction generator ran with unexpected error code. Is it licensed?')

    def test_fast_grow_available(self):
        """Test the fast grow binary exists and is licensed"""
        self.assertTrue(
            os.path.exists(FAST_GROW), f'Fast Grow binary does not exist at {FAST_GROW}')
        completed_process = subprocess.run(
            FAST_GROW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        # 64 == ArgumentError, which means the preprocessor is ready to accept arguments
        self.assertEqual(completed_process.returncode, 64,
                         'Fast Grow ran with unexpected error code. Is it licensed?')

    def test_interactions(self):
        """Test generating interactions"""
        ensemble = single_ensemble_with_ligand()
        search_point_data = SearchPointData(
            ligand=ensemble.ligand_set.first(), complex=ensemble.complex_set.first())
        search_point_data.save()
        generate_interactions.run(search_point_data.id)
        search_point_data = SearchPointData.objects.get(id=search_point_data.id)
        self.assertEqual(search_point_data.status, Status.SUCCESS)
        self.assertIsNotNone(search_point_data.data)

    def test_growing(self):
        """Test fast grow processes a growing"""
        growing = test_growing()
        try:
            grow.run(growing.id)
        finally:
            delete_test_fragment_set(growing.fragment_set.name)
        growing = Growing.objects.get(id=growing.id)
        self.assertEqual(growing.hit_set.count(), 10)
        growing_dict = growing.dict(detail=True)
        self.assertEqual(growing_dict['status'], 'success')
        self.assertEqual(
            growing_dict['hits'],
            sorted(growing_dict['hits'], key=lambda x: x['score'])
        )

    def test_growing_with_search_points(self):
        """Test fast grow processes a growing with search points"""
        growing = search_point_growing()
        try:
            grow.run(growing.id)
        finally:
            delete_test_fragment_set(growing.fragment_set.name)
        growing = Growing.objects.get(id=growing.id)
        self.assertEqual(growing.hit_set.count(), 10)
        growing_dict = growing.dict()
        self.assertEqual(growing_dict['status'], 'success')

    def test_growing_with_ensemble(self):
        """Test fast grow processes a growing using an ensemble"""
        growing = ensemble_growing()
        try:
            grow.run(growing.id)
        finally:
            delete_test_fragment_set(growing.fragment_set.name)
        growing = Growing.objects.get(id=growing.id)
        self.assertEqual(growing.hit_set.count(), 10)
        growing_dict = growing.dict()
        self.assertEqual(growing_dict['status'], 'success')
        self.assertEqual(
            len(growing_dict['hits'][0]['ensemble_scores']),
            growing.ensemble.complex_set.count()
        )

    def test_growing_fail(self):
        """Test fast grow processes a growing"""
        growing = test_growing()
        growing.fragment_set.name = 'fake'
        growing.fragment_set.save()
        try:
            grow.run(growing.id)
        except subprocess.CalledProcessError:
            growing = Growing.objects.get(id=growing.id)
            self.assertEqual(growing.status, Status.FAILURE)
        finally:
            delete_test_fragment_set('test_fragment_set')
