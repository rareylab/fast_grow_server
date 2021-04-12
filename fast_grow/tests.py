import json
import os
import subprocess
from datetime import datetime
from django.test import TestCase
from django.conf import settings
from fast_grow_server import celery_app  # TODO find a more general import for the celery app
from .models import Complex, Ligand, Interaction, Status
from .tasks import preprocess_complex


class ComplexModelTests(TestCase):

    def test_write_temp(self):
        complex_string = 'test string'
        cmplx = Complex(name='test', file_type='pdb', file_string=complex_string)
        complex_file = cmplx.write_temp()
        self.assertIn(cmplx.name, complex_file.name)
        self.assertEqual(complex_file.name[-3:], cmplx.file_type)
        self.assertEqual(complex_file.read(), complex_string)


class LigandModelTests(TestCase):

    def test_write_temp(self):
        ligand_string = 'test string'
        ligand = Ligand(name='test', file_type='sdf', file_string=ligand_string)
        ligand_file = ligand.write_temp()
        self.assertIn(ligand.name, ligand_file.name)
        self.assertEqual(ligand_file.name[-3:], ligand.file_type)
        self.assertEqual(ligand_file.read(), ligand_string)


class TaskTests(TestCase):

    def test_preprocessor_available(self):
        path = os.path.join(settings.BASE_DIR, 'bin', 'preprocessor')
        self.assertTrue(os.path.exists(path), 'Preprocessor binary does not exist at {}'.format(path))
        completed_process = subprocess.run(path, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # 64 == ArgumentError, which means the preprocessor is ready to accept arguments
        self.assertEqual(completed_process.returncode, 64,
                         'Preprocessor ran with unexpected error code. Is it licensed?')

    def test_preprocess_complex(self):
        with open('fast_grow/test_files/4agm.pdb') as f:
            complex_string = f.read()
        cmplx = Complex(name='4agm', file_type='pdb', file_string=complex_string, accessed=datetime.now())
        cmplx.save()

        preprocess_complex.run(cmplx.id)
        cmplx = Complex.objects.get(id=cmplx.id)
        self.assertEqual(cmplx.status, Status.SUCCESS)
        self.assertEqual(cmplx.ligand_set.count(), 2)
        self.assertEqual(cmplx.interaction_set.count(), 52)
        self.assertEqual(cmplx.interaction_set.filter(water_interaction=True).count(), 24)

    def test_preprocess_complex_with_ligand(self):
        with open('fast_grow/test_files/4agm.pdb') as f:
            complex_string = f.read()
        cmplx = Complex(name='4agm', file_type='pdb', file_string=complex_string, accessed=datetime.now())
        cmplx.save()

        with open('fast_grow/test_files/P86_A_400.sdf') as f:
            ligand_string = f.read()
        ligand = Ligand(name='P86_A_400', file_type='sdf', file_string=ligand_string, complex=cmplx)
        ligand.save()

        preprocess_complex.run(cmplx.id)
        cmplx = Complex.objects.get(id=cmplx.id)
        self.assertEqual(cmplx.status, Status.SUCCESS)
        self.assertEqual(cmplx.ligand_set.count(), 1)
        self.assertEqual(cmplx.interaction_set.count(), 26)
        self.assertEqual(cmplx.interaction_set.filter(water_interaction=True).count(), 12)


class ViewTests(TestCase):

    def setUp(self):
        celery_app.conf.update(CELERY_ALWAYS_EAGER=True)

    def test_complex_create(self):
        with open('fast_grow/test_files/4agm.pdb') as f:
            response = self.client.post('/complex', {'complex': f})
        self.assertEqual(response.status_code, 201)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertEqual(response_json['status'], Status.to_string(Status.PENDING))

    def test_complex_detail(self):
        with open('fast_grow/test_files/4agm.pdb') as f:
            complex_string = f.read()
        cmplx = Complex(name='4agm', file_type='pdb', file_string=complex_string, accessed=datetime.now())
        cmplx.save()

        with open('fast_grow/test_files/P86_A_400.sdf') as f:
            ligand_string = f.read()
        ligand = Ligand(name='P86_A_400', file_type='sdf', file_string=ligand_string, complex=cmplx)
        ligand.save()

        with open('fast_grow/test_files/P86_A_400_interactions.json') as f:
            data = json.load(f)
        interactions = data['interactions']
        for interaction in interactions:
            interctn = Interaction(json_interaction=json.dumps(interaction), water_interaction=False, ligand=ligand,
                                   complex=cmplx)
            interctn.save()

        response = self.client.get('/complex/{}'.format(cmplx.id))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertIn('file_string', response_json)
        self.assertIn('ligands', response_json)
        self.assertIn('interactions', response_json)
