"""Django view tests"""
import json
import os
import subprocess
from django.test import TestCase
from fast_grow_server import celery_app
from fast_grow.models import Core, Status
from .fixtures import TEST_FILES, processed_single_ensemble, test_ligand, test_core, \
    test_fragment_set, processed_growing, processed_search_points,\
    processed_ensemble_search_point_growing


class ViewTests(TestCase):
    """Django view tests"""

    def setUp(self):
        """setUp ensures no celery tasks are actually submitted by the views"""
        celery_app.conf.update(CELERY_ALWAYS_EAGER=True)

    def test_create_complex(self):
        """Test the complex create route creates a complex model"""
        with open(os.path.join(TEST_FILES, '4agm.pdb')) as complex_file:
            response = self.client.post('/complex', {'ensemble[]': [complex_file]})
        self.assertEqual(response.status_code, 201)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertEqual(len(response_json['complexes']), 1)
        self.assertEqual(response_json['status'], Status.to_string(Status.PENDING))

    def test_create_complex_with_ligand(self):
        """Test the complex create route creates a complex model with a custom ligand"""
        with open(os.path.join(TEST_FILES, '4agm.pdb')) as complex_file:
            with open(os.path.join(TEST_FILES, 'P86_A_400.sdf')) as ligand_file:
                response = self.client.post('/complex',
                                            {'ensemble[]': [complex_file], 'ligand': ligand_file})
        self.assertEqual(response.status_code, 201)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertEqual(len(response_json['complexes']), 1)
        self.assertEqual(len(response_json['ligands']), 1)
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
            response = self.client.post('/complex', {'ensemble[]': [ligand_file]})
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'complex is not a PDB file (.pdb)')

        # ligand not an SD file
        with open(os.path.join(TEST_FILES, '4agm.pdb')) as complex_file:
            response = self.client.post('/complex',
                                        {'ensemble[]': [complex_file], 'ligand': complex_file})
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
        ensemble = processed_single_ensemble()
        response = self.client.get('/complex/{}'.format(ensemble.id))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertIn('complexes', response_json)
        self.assertIn('ligands', response_json)

    def test_detail_fail(self):
        """Test the complex detail route return 404 for an unknown complex"""
        response = self.client.get('/complex/{}'.format(404))
        self.assertEqual(response.status_code, 404)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'model not found')

    def test_core_create(self):
        """Test the core create route creates a core based on a ligand"""
        ligand = test_ligand()
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

        ligand = test_ligand()

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
        ligand = test_ligand()
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

    def test_interactions_create(self):
        ensemble = processed_single_ensemble()
        response = self.client.post(
            '/interactions',
            data={
                'ligand_id': ensemble.ligand_set.first().id,
                'complex_id': ensemble.complex_set.first().id
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertEqual(Status.to_string(Status.PENDING), response_json['status'])

    def test_interactions_detail(self):
        search_point_data = processed_search_points()
        response = self.client.get('/interactions/{}'.format(search_point_data.id))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertIn('ligand_id', response_json)
        self.assertIn('complex_id', response_json)
        self.assertIn('data', response_json)
        self.assertIn('status', response_json)

    def test_growing_create(self):
        """Test the growing create route creates and starts a growing"""
        ensemble = processed_single_ensemble()
        ligand = ensemble.ligand_set.first()
        core = test_core(ligand)
        fragment_set = test_fragment_set()
        try:
            response = self.client.post(
                '/growing',
                {'ensemble': ensemble.id, 'core': core.id, 'fragment_set': fragment_set.id},
                content_type='application/json'
            )
        finally:
            subprocess.check_call(['dropdb', '-h', 'localhost', fragment_set.name])
        self.assertEqual(response.status_code, 201)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertEqual(Status.to_string(Status.PENDING), response_json['status'])

    def test_growing_create_with_search_points(self):
        """Test the growing create route creates and starts a growing with search points"""
        ensemble = processed_single_ensemble()
        core = test_core(ensemble.ligand_set.first())
        fragment_set = test_fragment_set()
        try:
            response = self.client.post(
                '/growing',
                json.dumps({
                    'ensemble': ensemble.id,
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
            subprocess.check_call(['dropdb', '-h', 'localhost', fragment_set.name])
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
            '/growing', data={'ensemble': 'fake'}, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'no core specified')

        # fragment set must be specified
        response = self.client.post(
            '/growing', data={'ensemble': 'fake', 'core': 'fake'}, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'no fragment set specified')

        # fragment set must be specified
        response = self.client.post(
            '/growing',
            data={'ensemble': 'fake', 'core': 'fake', 'fragment_set': 'fake'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        response_json = response.json()
        self.assertEqual(response_json['error'], 'an ID is not an integer')

    def test_growing_detail(self):
        """Test the growing detail route returns detailed information about a growing"""
        growing = processed_growing()
        nof_hits = 3
        try:
            response = self.client.get('/growing/{}'.format(growing.id), {
                'detail': True,
                'nof_hits': nof_hits
            })
        finally:
            subprocess.check_call(['dropdb', '-h', 'localhost', growing.fragment_set.name])
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertIn('id', response_json)
        self.assertIn('ensemble', response_json)
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
        growing = processed_growing()
        try:
            response = self.client.get('/growing/{}'.format(growing.id), {'nof_hits': 'fake'})
            self.assertEqual(response.status_code, 400)
            response_json = response.json()
            self.assertEqual(response_json['error'], 'invalid value for nof_hits')
        finally:
            subprocess.check_call(['dropdb', '-h', 'localhost', growing.fragment_set.name])

    def test_growing_download(self):
        growing = processed_ensemble_search_point_growing()
        try:
            response = self.client.get('/growing/{}/download'.format(growing.id))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'application/x-zip-compressed')
        finally:
            subprocess.check_call(['dropdb', '-h', 'localhost', growing.fragment_set.name])
