"""Test fixtures"""
import os
import json
import subprocess
from fast_grow_server import settings
from fast_grow.models import Complex, Core, FragmentSet, Growing, Ligand, \
    SearchPointData, Status
from fast_grow.tool_wrappers.fast_grow_wrapper import  FastGrowWrapper

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
            name='4agm', file_type='pdb', file_string=complex_string)
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
        name='4agm', file_type='pdb', file_string=complex_string)
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
        status=Status.SUCCESS
    )
    cmplx.save()

    with open(os.path.join(TEST_FILES, 'P86_A_400.sdf')) as ligand_file:
        ligand_string = ligand_file.read()
    ligand = Ligand(name='P86_A_400', file_type='sdf', file_string=ligand_string, complex=cmplx)
    ligand.save()
    return ligand


def create_core(ligand):
    """create a test core from a ligand"""
    with open(os.path.join(TEST_FILES, 'P86_A_400_18_2.sdf')) as core_file:
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


def create_fragment_set():
    """create a test fragment set"""
    fragment_set_name = 'test_fragment_set'
    fragment_set_path = os.path.join(TEST_FILES, 'test_fragment_set.tar')
    subprocess.check_call(['createdb', fragment_set_name])
    subprocess.check_call(['pg_restore', '-d', fragment_set_name, fragment_set_path])
    fragment_set = FragmentSet(name=fragment_set_name)
    fragment_set.save()
    return fragment_set


def create_test_growing(search_points=False, status=Status.PENDING):
    """create a test growing"""
    with open(os.path.join(TEST_FILES, '4agm_clean.pdb')) as complex_file:
        complex_string = complex_file.read()
    cmplx = Complex(
        name='4agm',
        file_type='pdb',
        file_string=complex_string,
        status=Status.SUCCESS
    )
    cmplx.save()

    # ensemble = None
    # if use_ensemble:
    #     with open(os.path.join(TEST_FILES, '4agn_clean.pdb')) as complex_file2:
    #         complex_string2 = complex_file2.read()
    #     cmplx2 = Complex(
    #         name='4agn',
    #         file_type='pdb',
    #         file_string=complex_string2,
    #         status=Status.SUCCESS
    #     )
    #     cmplx2.save()
    #
    #     with open(os.path.join(TEST_FILES, '4ago_clean.pdb')) as complex_file3:
    #         complex_string3 = complex_file3.read()
    #     cmplx3 = Complex(
    #         name='4ago',
    #         file_type='pdb',
    #         file_string=complex_string3,
    #         status=Status.SUCCESS
    #     )
    #     cmplx3.save()
    #
    #     ensemble = Ensemble()
    #     ensemble.save()
    #     ensemble.proteins.add(cmplx)
    #     ensemble.proteins.add(cmplx2)
    #     ensemble.proteins.add(cmplx3)
    #     ensemble.save()

    with open(os.path.join(TEST_FILES, 'P86_A_400.sdf')) as ligand_file:
        ligand_string = ligand_file.read()
    ligand = Ligand(name='P86_A_400', file_type='sdf', file_string=ligand_string, complex=cmplx)
    ligand.save()

    core = create_core(ligand)
    fragment_set = create_fragment_set()

    growing = Growing(core=core, fragment_set=fragment_set, complex=cmplx)
    if search_points:
        growing.search_points = '{"type":"MATCH","mode":"INCLUDE","radius":3,"searchPoint":' \
                                '{"position":[91.181,91.888,-46.398],"type":"HYDROPHOBIC"}}'
    growing.save()
    if status == Status.SUCCESS:
        FastGrowWrapper.add_hits(growing, os.path.join(TEST_FILES, 'P86_A_400_18_2_hits.sdf'))
    return growing
