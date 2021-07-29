from datetime import datetime
import json
import os
from django.test import TestCase
from fast_grow_server import celery_app, settings
from fast_grow.models import Complex, Ligand, Status, SearchPointData

TEST_FILES = os.path.join(settings.BASE_DIR, 'fast_grow', 'tests', 'test_files')


class ViewTests(TestCase):
    """Django view tests"""

    def setUp(self):
        """setUp ensures no celery tasks are actually submitted by the views"""
        celery_app.conf.update(CELERY_ALWAYS_EAGER=True)

    def test_create_complex(self):
        """Test the complex create route creates a complex model"""
        with open(os.path.join(TEST_FILES, '4agm.pdb')) as complex_file:
            response = self.client.post('/complex', {'complex': complex_file})
        self.assertEqual(response.status_code, 201)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertEqual(response_json['status'], Status.to_string(Status.PENDING))

    def test_create_complex_with_ligand(self):
        with open(os.path.join(TEST_FILES, '4agm.pdb')) as complex_file:
            with open(os.path.join(TEST_FILES, 'P86_A_400.sdf')) as ligand_file:
                response = self.client.post('/complex',
                                            {'complex': complex_file, 'ligand': ligand_file})
        self.assertEqual(response.status_code, 201)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertEqual(response_json['status'], Status.to_string(Status.PENDING))

    def test_create_complex_with_pdb_code(self):
        response = self.client.post('/complex', {'pdb': '4agm'})
        self.assertEqual(response.status_code, 201)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertEqual(response_json['status'], Status.to_string(Status.PENDING))

    def test_create_complex_with_pdb_code_and_ligand(self):
        with open(os.path.join(TEST_FILES, 'P86_A_400.sdf')) as ligand_file:
            response = self.client.post('/complex', {'pdb': '4agm', 'ligand': ligand_file})
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

        with open(os.path.join(TEST_FILES, 'P86_A_400.sdf')) as ligand_file:
            response = self.client.post('/complex', {'complex': ligand_file})
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'complex is not a PDB file (.pdb)')

        with open(os.path.join(TEST_FILES, '4agm.pdb')) as complex_file:
            response = self.client.post('/complex',
                                        {'complex': complex_file, 'ligand': complex_file})
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'ligand is not an SD file (.sdf)')

        response = self.client.post('/complex', {'pdb': '!@#$'})
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'invalid PDB code')

        response = self.client.post('/complex', {'pdb': '6666'})
        self.assertEqual(response.status_code, 404)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'invalid PDB code')

    def test_detail_complex(self):
        """Test the complex detail route returns all information for a complex"""
        with open(os.path.join(TEST_FILES, '4agm.pdb')) as complex_file:
            complex_string = complex_file.read()
        cmplx = Complex(
            name='4agm', file_type='pdb', file_string=complex_string, accessed=datetime.now())
        cmplx.save()

        with open(os.path.join(TEST_FILES, 'P86_A_400.sdf')) as ligand_file:
            ligand_string = ligand_file.read()
        ligand = Ligand(name='P86_A_400', file_type='sdf', file_string=ligand_string, complex=cmplx)
        ligand.save()

        with open(os.path.join(TEST_FILES, 'P86_A_400_search_points.json')) as search_points_file:
            data = json.load(search_points_file)
        search_point_data = SearchPointData(
            data=json.dumps(data),
            ligand=ligand,
            complex=cmplx
        )
        search_point_data.save()

        response = self.client.get('/complex/{}'.format(cmplx.id))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertIn('file_string', response_json)
        self.assertIn('ligands', response_json)
        self.assertIn('search_point_data', response_json)

    def test_detail_fail(self):
        response = self.client.get('/complex/{}'.format(404))
        self.assertEqual(response.status_code, 404)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'model not found')
