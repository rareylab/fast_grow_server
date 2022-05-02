"""Test fixtures"""
import json
import os
import subprocess
from fast_grow_server import settings
from fast_grow.models import Core, Complex, Ensemble, FragmentSet, Growing, Hit, Ligand, \
    SearchPointData, Status

TEST_FILES = os.path.join(settings.BASE_DIR, 'fast_grow', 'tests', 'test_files')


def multi_ensemble():
    """Create an ensemble with multiple complexes

    :return: ensemble with multiple complexes
    :rtype: Ensemble
    """
    ensemble = Ensemble()
    ensemble.save()

    with open(os.path.join(TEST_FILES, '4agm_clean.pdb'), encoding='utf8') as complex_file:
        complex_string_4agm = complex_file.read()
    complex_4agm = \
        Complex(ensemble=ensemble, name='4agm', file_type='pdb', file_string=complex_string_4agm)
    complex_4agm.save()

    with open(os.path.join(TEST_FILES, '4agn_clean.pdb'), encoding='utf8') as complex_file:
        complex_string_4agn = complex_file.read()
    complex_4agn = \
        Complex(ensemble=ensemble, name='4agm', file_type='pdb', file_string=complex_string_4agn)
    complex_4agn.save()

    with open(os.path.join(TEST_FILES, 'P86_A_400.sdf'), encoding='utf8') as ligand_file:
        ligand_string = ligand_file.read()
    ligand = Ligand(name='P86_A_400', file_type='sdf', file_string=ligand_string, ensemble=ensemble)
    ligand.save()
    return ensemble


def single_ensemble():
    """Create an ensemble with a single complexes

    :return: ensemble with a single complex
    :rtype: Ensemble
    """
    ensemble = Ensemble()
    ensemble.save()

    with open(os.path.join(TEST_FILES, '4agm.pdb'), encoding='utf8') as complex_file:
        complex_string = complex_file.read()
    cmplx = Complex(ensemble=ensemble, name='4agm', file_type='pdb', file_string=complex_string)
    cmplx.save()
    return ensemble


def single_ensemble_with_ligand():
    """Create an ensemble with a single complexes and a ligand

    :return: ensemble with single protein and ligand
    :rtype: Ensemble
    """
    ensemble = Ensemble()
    ensemble.save()

    with open(os.path.join(TEST_FILES, '4agm_clean.pdb'), encoding='utf8') as complex_file:
        complex_string = complex_file.read()
    cmplx = Complex(ensemble=ensemble, name='4agm', file_type='pdb', file_string=complex_string)
    cmplx.save()

    with open(os.path.join(TEST_FILES, 'P86_A_400.sdf'), encoding='utf8') as ligand_file:
        ligand_string = ligand_file.read()
    ligand = Ligand(name='P86_A_400', file_type='sdf', file_string=ligand_string, ensemble=ensemble)
    ligand.save()
    return ensemble


def processed_single_ensemble():
    """Create a preprocessed ensemble with a single complexes

    :return: preprocessed ensemble with a single complexes
    :rtype: Ensemble
    """
    ensemble = Ensemble()
    ensemble.save()

    with open(os.path.join(TEST_FILES, '4agm_clean.pdb'), encoding='utf8') as complex_file:
        complex_string = complex_file.read()
    cmplx = Complex(ensemble=ensemble, name='4agm', file_type='pdb', file_string=complex_string)
    cmplx.save()

    with open(os.path.join(TEST_FILES, 'P86_A_400.sdf'), encoding='utf8') as ligand_file:
        ligand_string = ligand_file.read()
    ligand = Ligand(name='P86_A_400', file_type='sdf', file_string=ligand_string, ensemble=ensemble)
    ligand.save()

    return ensemble


def processed_ensemble():
    """Create a preprocessed ensemble with multiple single complexes

    :return: preprocessed ensemble with multiple single complexes
    :rtype: Ensemble
    """
    ensemble = Ensemble()
    ensemble.save()

    with open(os.path.join(TEST_FILES, '4agm_clean.pdb'), encoding='utf8') as complex_file:
        complex_string_4agm = complex_file.read()
    complex_4agm = \
        Complex(ensemble=ensemble, name='4agm', file_type='pdb', file_string=complex_string_4agm)
    complex_4agm.save()

    with open(os.path.join(TEST_FILES, '4agn_clean.pdb'), encoding='utf8') as complex_file:
        complex_string_4agn = complex_file.read()
    complex_4agn = \
        Complex(ensemble=ensemble, name='4agn', file_type='pdb', file_string=complex_string_4agn)
    complex_4agn.save()

    with open(os.path.join(TEST_FILES, 'P86_A_400.sdf'), encoding='utf8') as ligand_file:
        ligand_string = ligand_file.read()
    ligand = Ligand(name='P86_A_400', file_type='sdf', file_string=ligand_string, ensemble=ensemble)
    ligand.save()

    with open(os.path.join(TEST_FILES, 'P86_A_400_search_points.json'), encoding='utf8') \
            as search_points_file:
        data = json.load(search_points_file)
    search_point_data = SearchPointData(
        data=json.dumps(data),
        ligand=ligand,
        complex=complex_4agm
    )
    search_point_data.save()
    return ensemble


def test_ligand():
    """Create a test ligand

    :return: test ligand
    :rtype: Ligand
    """
    ensemble = Ensemble()
    ensemble.save()
    with open(os.path.join(TEST_FILES, 'P86_A_400.sdf'), encoding='utf8') as ligand_file:
        ligand_string = ligand_file.read()
    ligand = Ligand(name='P86_A_400', file_type='sdf', file_string=ligand_string, ensemble=ensemble)
    ligand.save()
    return ligand


def test_core(ligand):
    """Create a test core from a ligand

    :param ligand: ligand to generate the core for
    :type ligand: Ligand
    :return: test core
    :rtype: Core
    """
    with open(os.path.join(TEST_FILES, 'P86_A_400_18_2.sdf'), encoding='utf8') as core_file:
        core_string = core_file.read()
    core = Core(
        ligand=ligand,
        name='P86_A_400_18_2',
        anchor=18,
        linker=2,
        file_string=core_string,
        file_type='sdf',
        status=Status.SUCCESS
    )
    core.save()
    return core


def processed_search_points():
    """Create a set of processed search points

    :return: search point data
    :rtype: SearchPointData
    """
    ensemble = processed_single_ensemble()
    with open(os.path.join(TEST_FILES, 'P86_A_400_search_points.json'), encoding='utf8') \
            as search_point_file:
        data = search_point_file.read()
    search_point_data = SearchPointData(
        ligand=ensemble.ligand_set.first(),
        complex=ensemble.complex_set.first(),
        data=data,
        status=Status.SUCCESS
    )
    search_point_data.save()
    return search_point_data


def test_fragment_set():
    """Create a test fragment set

    Creates an actual database in the configured RDBMS.

    :return: test fragment set
    :rtype: FragmentSet
    """
    fragment_set_name = 'test_fragment_set'
    fragment_set_path = os.path.join(TEST_FILES, 'test_fragment_set.tar')
    subprocess.check_call([
        'createdb',
        '-h', settings.DATABASES['default']['HOST'],
        '-U', settings.DATABASES['default']['USER'],
        fragment_set_name
    ])
    subprocess.check_call([
        'pg_restore',
        '-h', settings.DATABASES['default']['HOST'],
        '-U', settings.DATABASES['default']['USER'],
        '-n', 'public',  # Only restore data from the public schema.
        '-d', fragment_set_name, fragment_set_path
    ])
    fragment_set = FragmentSet(name=fragment_set_name)
    fragment_set.save()
    return fragment_set


def delete_test_fragment_set(fragment_set_name):
    subprocess.check_call([
        'dropdb',
        '-h', settings.DATABASES['default']['HOST'],
        '-U', settings.DATABASES['default']['USER'],
        fragment_set_name
    ])


def test_growing():
    """Create a test growing

    :return: test growing
    :rtype: Growing
    """
    ensemble = processed_single_ensemble()
    core = test_core(ensemble.ligand_set.first())
    fragment_set = test_fragment_set()
    growing = Growing(ensemble=ensemble, core=core, fragment_set=fragment_set)
    growing.save()
    return growing


def search_point_growing():
    """Create a test growing with search points

    :return: test growing with search points
    :rtype: Growing
    """
    ensemble = processed_single_ensemble()
    core = test_core(ensemble.ligand_set.first())
    fragment_set = test_fragment_set()
    search_point = """
{
    "type": "MATCH",
    "mode": "INCLUDE",
    "radius": 3,
    "searchPoint": {
      "position": [
        91.181,
        91.888,
        -46.398
      ],
      "type": "HYDROPHOBIC"
    }
}"""
    growing = Growing(
        ensemble=ensemble,
        core=core,
        fragment_set=fragment_set,
        search_points=search_point
    )
    growing.save()
    return growing


def ensemble_growing():
    """Create a test ensemble growing

    :return: test ensemble growing
    :rtype: Growing
    """
    ensemble = processed_ensemble()
    core = test_core(ensemble.ligand_set.first())
    fragment_set = test_fragment_set()
    growing = Growing(ensemble=ensemble, core=core, fragment_set=fragment_set)
    growing.save()
    return growing


def processed_growing():
    """Create a processed ensemble growing

    :return: processed ensemble growing
    :rtype: Growing
    """
    ensemble = processed_single_ensemble()
    core = test_core(ensemble.ligand_set.first())
    fragment_set = test_fragment_set()
    growing = Growing(ensemble=ensemble, core=core, fragment_set=fragment_set)
    growing.save()
    for i in range(5):
        hit = Hit(
            growing=growing,
            name='hit' + str(i),
            score=0.0,
            file_type='sdf',
            file_string='',
            ensemble_scores={}
        )
        hit.save()
    return growing


def processed_ensemble_search_point_growing():
    """Create a processed growing with an ensemble and search points

    :return: processed growing with an ensemble and search points
    :rtype: Growing
    """
    ensemble = processed_ensemble()
    core = test_core(ensemble.ligand_set.first())
    fragment_set = test_fragment_set()
    search_point = """
    {
        "type": "MATCH",
        "mode": "INCLUDE",
        "radius": 3,
        "searchPoint": {
          "position": [
            91.181,
            91.888,
            -46.398
          ],
          "type": "HYDROPHOBIC"
        }
    }"""
    growing = Growing(
        ensemble=ensemble,
        core=core,
        fragment_set=fragment_set,
        search_points=search_point
    )
    growing.save()
    for i in range(5):
        hit = Hit(
            growing=growing,
            name='hit' + str(i),
            score=0.0,
            file_type='sdf',
            file_string='',
            ensemble_scores={}
        )
        hit.save()
    return growing
