"""Test fixtures"""
import os
import json
from datetime import datetime
from fast_grow_server import settings
from fast_grow.models import Complex, Ligand, SearchPointData, Status

TEST_FILES = os.path.join(settings.BASE_DIR, 'fast_grow', 'tests', 'test_files')


def create_test_complex(status=Status.PENDING, custom_ligand=False):
    """create a test complex

    :param status: status of the complex
    :param custom_ligand: complex has a custom ligand
    :return: created complex model
    """
    if status == Status.PENDING:
        with open(os.path.join(TEST_FILES, '4agm.pdb')) as complex_file:
            complex_string = complex_file.read()
        cmplx = Complex(
            name='4agm', file_type='pdb', file_string=complex_string, accessed=datetime.now())
        cmplx.save()

        if custom_ligand:
            with open(os.path.join(TEST_FILES, 'P86_A_400.sdf')) as ligand_file:
                ligand_string = ligand_file.read()
            ligand = Ligand(
                name='P86_A_400', file_type='sdf', file_string=ligand_string, complex=cmplx)
            ligand.save()

        return cmplx

    with open(os.path.join(TEST_FILES, '4agm_clean.pdb')) as complex_file:
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
    return cmplx


def create_test_ligand():
    """create a test ligand"""
    with open(os.path.join(TEST_FILES, '4agm_clean.pdb')) as complex_file:
        complex_string = complex_file.read()
    cmplx = Complex(
        name='4agm',
        file_type='pdb',
        file_string=complex_string,
        accessed=datetime.now(),
        status=Status.SUCCESS
    )
    cmplx.save()

    with open(os.path.join(TEST_FILES, 'P86_A_400.sdf')) as ligand_file:
        ligand_string = ligand_file.read()
    ligand = Ligand(name='P86_A_400', file_type='sdf', file_string=ligand_string, complex=cmplx)
    ligand.save()
    return ligand
