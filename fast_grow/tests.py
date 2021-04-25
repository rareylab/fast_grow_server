"""fast_grow tests"""
import json
import os
import subprocess
from datetime import datetime
from django.test import TestCase
from django.conf import settings
from fast_grow_server import celery_app  # TODO find a more general import for the celery app pylint: disable=fixme
from .models import Complex, Ligand, Interaction, Status
from .tasks import preprocess_complex


class StatusTests(TestCase):
    """Status enum tests"""

    def test_to_string(self):
        """Test to string method of status enum"""
        self.assertEqual(Status.to_string(Status.PENDING), 'pending')
        self.assertEqual(Status.to_string(Status.RUNNING), 'running')
        self.assertEqual(Status.to_string(Status.SUCCESS), 'success')
        self.assertEqual(Status.to_string(Status.FAILURE), 'failure')


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
        with open('fast_grow/test_files/4agm.pdb') as complex_file:
            complex_string = complex_file.read()
        cmplx = Complex(
            name='4agm', file_type='pdb', file_string=complex_string, accessed=datetime.now())
        cmplx.save()

        preprocess_complex.run(cmplx.id)
        cmplx = Complex.objects.get(id=cmplx.id)
        self.assertEqual(cmplx.status, Status.SUCCESS)
        self.assertEqual(cmplx.ligand_set.count(), 2)
        self.assertEqual(cmplx.interaction_set.count(), 52)
        self.assertEqual(cmplx.interaction_set.filter(water_interaction=True).count(), 24)

    def test_preprocess_complex_with_ligand(self):
        """Test the preprocessor correctly processes a complex with an explicitly set ligand"""
        with open('fast_grow/test_files/4agm.pdb') as complex_file:
            complex_string = complex_file.read()
        cmplx = Complex(
            name='4agm', file_type='pdb', file_string=complex_string, accessed=datetime.now())
        cmplx.save()

        with open('fast_grow/test_files/P86_A_400.sdf') as ligand_file:
            ligand_string = ligand_file.read()
        ligand = Ligand(
            name='P86_A_400', file_type='sdf', file_string=ligand_string, complex=cmplx)
        ligand.save()

        preprocess_complex.run(cmplx.id)
        cmplx = Complex.objects.get(id=cmplx.id)
        self.assertEqual(cmplx.status, Status.SUCCESS)
        self.assertEqual(cmplx.ligand_set.count(), 1)
        self.assertEqual(cmplx.interaction_set.count(), 26)
        self.assertEqual(cmplx.interaction_set.filter(water_interaction=True).count(), 12)

    def test_preprocess_fail(self):
        try:
            preprocess_complex.run(404)
        except Complex.DoesNotExist as error:
            self.assertEqual(str(error), 'Complex matching query does not exist.')

        with open('fast_grow/test_files/4agm.pdb') as complex_file:
            complex_string = complex_file.read()
        cmplx = Complex(
            name='4agm', file_type='pdb', file_string=complex_string, accessed=datetime.now())
        cmplx.save()

        with open('fast_grow/test_files/P86_A_400.sdf') as ligand_file:
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
            self.assertEqual(str(error), 'complex({}) to be processed has more than one ligand'.format(cmplx.id))


class ViewTests(TestCase):
    """Django view tests"""

    def setUp(self):
        """setUp ensures no celery tasks are actually submitted by the views"""
        celery_app.conf.update(CELERY_ALWAYS_EAGER=True)

    def test_create_complex(self):
        """Test the complex create route creates a complex model"""
        with open('fast_grow/test_files/4agm.pdb') as complex_file:
            response = self.client.post('/complex', {'complex': complex_file})
        self.assertEqual(response.status_code, 201)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertEqual(response_json['status'], Status.to_string(Status.PENDING))

    def test_create_complex_with_ligand(self):
        with open('fast_grow/test_files/4agm.pdb') as complex_file:
            with open('fast_grow/test_files/P86_A_400.sdf') as ligand_file:
                response = self.client.post('/complex', {'complex': complex_file, 'ligand': ligand_file})
        self.assertEqual(response.status_code, 201)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertEqual(response_json['status'], Status.to_string(Status.PENDING))

    def test_create_fail(self):
        response = self.client.get('/complex')
        response_json = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response_json['error'], 'bad request')

        response = self.client.post('/complex', {})
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'no complex specified')

        with open('fast_grow/test_files/P86_A_400.sdf') as ligand_file:
            response = self.client.post('/complex', {'complex': ligand_file})
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'complex is not a PDB file (.pdb)')

        with open('fast_grow/test_files/4agm.pdb') as complex_file:
            with open('fast_grow/test_files/P86_A_400.sdf') as ligand_file:
                response = self.client.post('/complex', {'complex': complex_file, 'ligand': complex_file})
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'ligand is not an SD file (.sdf)')

    def test_detail_complex(self):
        """Test the complex detail route returns all information for a complex"""
        with open('fast_grow/test_files/4agm.pdb') as complex_file:
            complex_string = complex_file.read()
        cmplx = Complex(
            name='4agm', file_type='pdb', file_string=complex_string, accessed=datetime.now())
        cmplx.save()

        with open('fast_grow/test_files/P86_A_400.sdf') as ligand_file:
            ligand_string = ligand_file.read()
        ligand = Ligand(name='P86_A_400', file_type='sdf', file_string=ligand_string, complex=cmplx)
        ligand.save()

        with open('fast_grow/test_files/P86_A_400_interactions.json') as interaction_file:
            data = json.load(interaction_file)
        interactions = data['interactions']
        for interaction in interactions:
            interctn = Interaction(
                json_interaction=json.dumps(interaction),
                water_interaction=False,
                ligand=ligand,
                complex=cmplx
            )
            interctn.save()

        response = self.client.get('/complex/{}'.format(cmplx.id))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertIn('file_string', response_json)
        self.assertIn('ligands', response_json)
        self.assertIn('interactions', response_json)

    def test_detail_fail(self):
        response = self.client.get('/complex/{}'.format(404))
        self.assertEqual(response.status_code, 404)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'model not found')
