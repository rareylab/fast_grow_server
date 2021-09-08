"""Django view tests"""
import json
import os
import subprocess
from django.test import TestCase
from fast_grow_server import celery_app
from fast_grow.models import Core, Status
from .fixtures import TEST_FILES, create_test_complex, create_test_ligand, \
    create_fragment_set, create_core, create_test_growing


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
        """Test the complex create route creates a complex model with a custom ligand"""
        with open(os.path.join(TEST_FILES, '4agm.pdb')) as complex_file:
            with open(os.path.join(TEST_FILES, 'P86_A_400.sdf')) as ligand_file:
                response = self.client.post('/complex',
                                            {'complex': complex_file, 'ligand': ligand_file})
        self.assertEqual(response.status_code, 201)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertEqual(response_json['status'], Status.to_string(Status.PENDING))

    def test_create_complex_with_pdb_code(self):
        """Test the complex create route creates a complex model with a pdb code"""
        response = self.client.post('/complex', {'pdb': '4agm'})
        self.assertEqual(response.status_code, 201)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertEqual(response_json['status'], Status.to_string(Status.PENDING))

    def test_create_complex_with_pdb_code_and_ligand(self):
        """Test the complex create route creates a complex model with a pdb code and a custom
         ligand"""
        with open(os.path.join(TEST_FILES, 'P86_A_400.sdf')) as ligand_file:
            response = self.client.post('/complex', {'pdb': '4agm', 'ligand': ligand_file})
        self.assertEqual(response.status_code, 201)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertEqual(response_json['status'], Status.to_string(Status.PENDING))

    def test_create_fail(self):
        """Test complex create route failures"""
        # must be post
        response = self.client.get('/complex')
        response_json = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response_json['error'], 'bad request')

        # no complex
        response = self.client.post('/complex', {})
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'no complex specified')

        # not a pdb file
        with open(os.path.join(TEST_FILES, 'P86_A_400.sdf')) as ligand_file:
            response = self.client.post('/complex', {'complex': ligand_file})
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'complex is not a PDB file (.pdb)')

        # ligand not an SD file
        with open(os.path.join(TEST_FILES, '4agm.pdb')) as complex_file:
            response = self.client.post('/complex',
                                        {'complex': complex_file, 'ligand': complex_file})
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'ligand is not an SD file (.sdf)')

        # invalid pdb code
        response = self.client.post('/complex', {'pdb': '!@#$'})
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'invalid PDB code')

        # pdb code that does not exist, or at least at time of writing
        response = self.client.post('/complex', {'pdb': '6666'})
        self.assertEqual(response.status_code, 404)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'invalid PDB code')

    def test_detail_complex(self):
        """Test the complex detail route returns all information for a complex"""
        cmplx = create_test_complex(Status.SUCCESS)
        response = self.client.get('/complex/{}'.format(cmplx.id))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertIn('file_string', response_json)
        self.assertIn('ligands', response_json)
        self.assertIn('search_point_data', response_json)

    def test_detail_fail(self):
        """Test the complex detail route return 404 for an unknown complex"""
        response = self.client.get('/complex/{}'.format(404))
        self.assertEqual(response.status_code, 404)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'model not found')

    def test_core_create(self):
        """Test the core create route creates a core based on a ligand"""
        ligand = create_test_ligand()
        response = self.client.post(
            '/core',
            {'ligand_id': ligand.id, 'anchor': 18, 'linker': 2},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        response_json = response.json()
        core_name = ligand.name + '_18_2'
        self.assertIn('id', response_json)
        self.assertEqual(Status.to_string(Status.PENDING), response_json['status'])
        self.assertEqual(core_name, response_json['name'])

    def test_core_create_fail(self):
        """Test core create failures"""
        # must contain ligand_id
        response = self.client.post('/core', content_type='application/json')
        response_json = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response_json['error'], 'no ligand specified')

        # ligand must exist
        response = self.client.post('/core', {'ligand_id': 404}, content_type='application/json')
        response_json = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response_json['error'], 'ligand does not exist')

        ligand = create_test_ligand()

        # must specify anchor and linker
        response = self.client.post(
            '/core',
            {'ligand_id': ligand.id},
            content_type='application/json'
        )
        response_json = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response_json['error'], 'no "anchor" or linker specified')

        # anchor and linker must be integers
        response = self.client.post(
            '/core',
            {'ligand_id': ligand.id, 'anchor': 'C', 'linker': 2},
            content_type='application/json'
        )
        response_json = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response_json['error'], 'invalid anchor or linker specified')

    def test_core_detail(self):
        """Test the core detail route returns all information about the core"""
        ligand = create_test_ligand()
        with open(os.path.join(TEST_FILES, 'P86_A_400_18_2.sdf')) as core_file:
            core_string = core_file.read()
        core = Core(
            name='P86_Afrom .task_tests import grow_400_18_2',
            ligand=ligand,
            anchor=18,
            linker=3,
            file_string=core_string,
            file_type='sdf',
            status=Status.SUCCESS
        )
        core.save()

        response = self.client.get('/core/{}'.format(core.id))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertIn('ligand_id', response_json)
        self.assertIn('name', response_json)
        self.assertIn('anchor', response_json)
        self.assertIn('linker', response_json)
        self.assertIn('status', response_json)
        self.assertIn('file_type', response_json)
        self.assertIn('file_string', response_json)

    def test_core_detail_fail(self):
        """Test the core detail route returns 404 for an unknown complex"""
        response = self.client.get('/core/{}'.format(404))
        self.assertEqual(response.status_code, 404)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'model not found')

    def test_growing_create(self):
        """Test the growing create route creates and starts a growing"""
        cmplx = create_test_complex(Status.SUCCESS)
        ligand = cmplx.ligand_set.first()
        core = create_core(ligand)
        fragment_set = create_fragment_set()
        try:
            response = self.client.post(
                '/growing',
                {'complex': cmplx.id, 'core': core.id, 'fragment_set': fragment_set.id},
                content_type='application/json'
            )
        finally:
            subprocess.check_call(['dropdb', fragment_set.name])
        print(response.json())
        self.assertEqual(response.status_code, 201)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertEqual(Status.to_string(Status.PENDING), response_json['status'])

    def test_growing_create_with_search_points(self):
        """Test the growing create route creates and starts a growing with search points"""
        cmplx = create_test_complex(Status.SUCCESS)
        ligand = cmplx.ligand_set.first()
        core = create_core(ligand)
        fragment_set = create_fragment_set()
        try:
            response = self.client.post(
                '/growing',
                json.dumps({
                    'complex': cmplx.id,
                    'core': core.id,
                    'fragment_set': fragment_set.id,
                    'search_points': {
                        'type': 'MATCH',
                        'mode': 'INCLUDE',
                        'radius': 3,
                        'searchPoint': {
                            'position': [91.181, 91.888, -46.398],
                            'type': 'HYDROPHOBIC'
                        }
                    }
                }),
                content_type='application/json')
        finally:
            subprocess.check_call(['dropdb', fragment_set.name])
        self.assertEqual(response.status_code, 201)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertEqual(Status.to_string(Status.PENDING), response_json['status'])

    def test_growing_create_fail(self):
        """Test growing create route fails"""
        # request should be post
        response = self.client.get('/growing')
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'bad request')

        # request should be application/json
        response = self.client.post('/growing', data='fake data', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'bad request')

        # complex must be specified
        response = self.client.post('/growing', data={}, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'no complex specified')

        # core must be specified
        response = self.client.post(
            '/growing', data={'complex': 'fake'}, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'no core specified')

        # fragment set must be specified
        response = self.client.post(
            '/growing', data={'complex': 'fake', 'core': 'fake'}, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'no fragment set specified')

        # fragment set must be specified
        response = self.client.post(
            '/growing',
            data={'complex': 'fake', 'core': 'fake', 'fragment_set': 'fake'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'an ID is not an integer')

    def test_growing_detail(self):
        """Test the growing detail route returns detailed information about a growing"""
        growing = create_test_growing(search_points=True, status=Status.SUCCESS)
        nof_hits = 3
        try:
            response = self.client.get('/growing/{}'.format(growing.id), {
                'detail': True,
                'nof_hits': nof_hits
            })
        finally:
            subprocess.check_call(['dropdb', growing.fragment_set.name])
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertIn('complex', response_json)
        self.assertIn('core', response_json)
        self.assertIn('fragment_set', response_json)
        self.assertIn('search_points', response_json)
        self.assertIn('status', response_json)
        self.assertIn('hits', response_json)
        self.assertEqual(len(response_json['hits']), nof_hits)

    def test_growing_detail_fail(self):
        """Test growing detail route fails"""
        # growing does not exist
        response = self.client.get('/growing/{}'.format(1), {'nof_hits': 100})
        self.assertEqual(response.status_code, 404)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'model not found')

        # nof_hits must be an int
        growing = create_test_growing(search_points=True, status=Status.SUCCESS)
        try:
            response = self.client.get('/growing/{}'.format(growing.id), {'nof_hits': 'fake'})
            self.assertEqual(response.status_code, 400)
            response_json = response.json()
            self.assertEqual(response_json['error'], 'invalid value for nof_hits')
        finally:
            subprocess.check_call(['dropdb', growing.fragment_set.name])
