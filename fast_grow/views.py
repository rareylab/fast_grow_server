"""fast_grow views"""
import os
import json
import re
import urllib.request
import urllib.error
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from fast_grow_server import settings
from .models import Complex, Core, FragmentSet, Growing, Ligand, Ensemble, SearchPointData
from .tasks import preprocess_ensemble, clip_ligand, grow, generate_interactions


@csrf_exempt
def complex_create(request):
    """Create a complex using file uploads or a pdb code

    If a ligand is uploaded as well, this ligand is associated with the complex. Schedules a celery
    job to preprocess the complex.

    :param request: ensemble upload
    :return: ensemble model
    :rtype: JsonResponse
    """
    # this could be a decorator but I prefer the control
    if request.method != 'POST':
        return JsonResponse({'error': 'bad request'}, status=400)

    ensemble = Ensemble()
    ensemble.save()
    if 'ensemble[]' in request.FILES:
        for complex_file in request.FILES.pop('ensemble[]'):
            complex_filename, complex_extension = os.path.splitext(complex_file.name)
            if complex_extension != '.pdb':
                return JsonResponse({'error': 'complex is not a PDB file (.pdb)'}, status=400)

            complex_name = os.path.basename(complex_filename)[:255]  # name has max size of 255
            complex_string = complex_file.read().decode('utf8')
            cmplx = Complex(
                name=complex_name,
                file_type=complex_extension[1:],  # remove period at the beginning of the extension
                file_string=complex_string,
                ensemble=ensemble
            )
            cmplx.save()
    elif 'pdb' in request.POST:
        pdb_code = request.POST['pdb'].lower()
        if not re.match(r'[a-z0-9]{4}', pdb_code):
            return JsonResponse({'error': 'invalid PDB code'}, status=400)

        pdb_url = settings.PDB_FILE_URL.format(pdb_code)
        try:
            with urllib.request.urlopen(pdb_url, timeout=10) as pdb_stream:
                complex_string = pdb_stream.read().decode('utf-8')
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return JsonResponse({'error': 'invalid PDB code'}, status=404)
            return JsonResponse({'error': 'bad request'}, status=400)

        cmplx = Complex(
            name=pdb_code,
            file_type='pdb',
            file_string=complex_string,
            ensemble=ensemble
        )
        cmplx.save()
        ensemble.complex_set.add(cmplx)
    else:
        return JsonResponse({'error': 'no complex specified'}, status=400)

    if 'ligand' in request.FILES:
        ligand_filename, ligand_extension = os.path.splitext(request.FILES['ligand'].name)
        if ligand_extension != '.sdf':
            return JsonResponse({'error': 'ligand is not an SD file (.sdf)'}, status=400)

        ligand_name = os.path.basename(ligand_filename)[:255]  # name has max size of 255
        ligand_string = request.FILES['ligand'].read().decode('utf8')
        ligand = Ligand(
            name=ligand_name,
            file_type=ligand_extension[1:],  # remove period
            file_string=ligand_string,
            ensemble=ensemble
        )
        ligand.save()
    preprocess_ensemble.delay(ensemble.id)
    return JsonResponse(ensemble.dict(), status=201, safe=False)


@csrf_exempt
def complex_detail(request, ensemble_id):
    """Get detailed information of a complex

    :param request: ensemble request
    :param ensemble_id: id of an ensemble
    :type ensemble_id: int
    :return: ensemble model or not found
    :rtype: JsonResponse
    """
    try:
        ensemble = Ensemble.objects.get(id=ensemble_id)
    except Ensemble.DoesNotExist:
        return JsonResponse({'error': 'model not found'}, status=404)
    return JsonResponse(ensemble.dict(detail=True), status=200, safe=False)


@csrf_exempt
def core_create(request):
    """Create a core using a ligand

    :param request: ligand clipping request
    :return: core model
    :rtype: JsonResponse
    """
    # this could be a decorator but I prefer the control
    if request.method != 'POST' or request.content_type != 'application/json':
        return JsonResponse({'error': 'bad request'}, status=400)
    try:
        request_json = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'bad request'}, status=400)

    if 'ligand_id' not in request_json:
        return JsonResponse({'error': 'no ligand specified'}, status=400)

    try:
        ligand = Ligand.objects.get(id=request_json['ligand_id'])
    except Ligand.DoesNotExist:
        return JsonResponse({'error': 'ligand does not exist'}, status=400)

    if 'anchor' not in request_json or 'linker' not in request_json:
        return JsonResponse({'error': 'no "anchor" or linker specified'}, status=400)

    try:
        anchor = int(request_json['anchor'])
        linker = int(request_json['linker'])
    except ValueError:
        return JsonResponse({'error': 'invalid anchor or linker specified'}, status=400)

    core = Core(
        ligand=ligand,
        name=ligand.name + '_' + str(anchor) + '_' + str(linker),
        anchor=anchor,
        linker=linker
    )
    core.save()
    clip_ligand.delay(core.id)
    return JsonResponse(core.dict(), status=201, safe=False)


@csrf_exempt
def core_detail(request, core_id):
    """Get detailed information of a core

    :param request: core request
    :param core_id: core id
    :type core_id: int
    :return: core model or not found
    :rtype: JsonResponse
    """
    try:
        core = Core.objects.get(id=core_id)
    except Core.DoesNotExist:
        return JsonResponse({'error': 'model not found'}, status=404)
    return JsonResponse(core.dict(detail=True), status=200, safe=False)


@csrf_exempt
def interactions_create(request):
    """Generate interactions for specified ligand and complex

    :param request: interactions generation request
    :return: search point data model
    :rtype: JsonResponse
    """
    # this could be a decorator but I prefer the control
    if request.method != 'POST' or request.content_type != 'application/json':
        return JsonResponse({'error': 'bad request'}, status=400)
    try:
        request_json = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'bad request'}, status=400)

    if 'ligand_id' not in request_json:
        return JsonResponse({'error': 'no ligand specified'}, status=400)

    try:
        ligand = Ligand.objects.get(id=request_json['ligand_id'])
    except Ligand.DoesNotExist:
        return JsonResponse({'error': 'ligand does not exist'}, status=400)

    if 'complex_id' not in request_json:
        return JsonResponse({'error': 'no complex specified'}, status=400)

    try:
        cmplx = Complex.objects.get(id=request_json['complex_id'])
    except Complex.DoesNotExist:
        return JsonResponse({'error': 'complex does not exist'}, status=400)

    search_point_data = SearchPointData(ligand=ligand, complex=cmplx)
    search_point_data.save()
    generate_interactions.delay(search_point_data.id)
    return JsonResponse(search_point_data.dict(), status=201, safe=False)


@csrf_exempt
def interactions_detail(request, search_point_data_id):
    """Get detailed interaction data

    :param request: interaction request
    :param search_point_data_id: search point data id
    :type search_point_data_id: int
    :return: search point data model
    :rtype: JsonResponse
    """
    try:
        search_point_data = SearchPointData.objects.get(id=search_point_data_id)
    except SearchPointData.DoesNotExist:
        return JsonResponse({'error': 'model not found'}, status=404)
    return JsonResponse(search_point_data.dict(detail=True), status=200, safe=False)


@csrf_exempt
def growing_create(request):
    """Create a growing

    :param request: growing request
    :return: growing model
    :rtype: JsonResponse
    """
    # this could be a decorator but I prefer the control
    if request.method != 'POST' or request.content_type != 'application/json':
        return JsonResponse({'error': 'bad request'}, status=400)
    try:
        request_json = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'bad request'}, status=400)

    if 'ensemble' not in request_json:
        return JsonResponse({'error': 'no complex specified'}, status=400)

    if 'core' not in request_json:
        return JsonResponse({'error': 'no core specified'}, status=400)

    if 'fragment_set' not in request_json:
        return JsonResponse({'error': 'no fragment set specified'}, status=400)

    try:
        ensemble = Ensemble.objects.get(id=int(request_json['ensemble']))
        core = Core.objects.get(id=int(request_json['core']))
        fragment_set = FragmentSet.objects.get(id=int(request_json['fragment_set']))
    except ValueError:
        return JsonResponse({'error': 'an ID is not an integer'}, status=400)
    except Complex.DoesNotExist:
        return JsonResponse({'error': 'complex does not exist'}, status=400)
    except Core.DoesNotExist:
        return JsonResponse({'error': 'core does not exist'}, status=400)
    except FragmentSet.DoesNotExist:
        return JsonResponse({'error': 'fragment set does not exist'}, status=400)

    search_points = None
    if 'search_points' in request_json:
        search_points = request_json['search_points']

    growing = Growing(
        ensemble=ensemble,
        core=core,
        fragment_set=fragment_set,
        search_points=json.dumps(search_points) if search_points else None
    )
    growing.save()
    grow.delay(growing.id)
    return JsonResponse(growing.dict(), status=201, safe=False)


@csrf_exempt
def growing_detail(request, growing_id):
    """Get detailed information of a growing

    :param request: growing request
    :param growing_id: id of a growing
    :type growing_id: int
    :return: growing model or not found
    :rtype: JsonResponse
    """
    try:
        growing = Growing.objects.get(id=growing_id)
        detail = request.GET['detail'] if 'detail' in request.GET else False
        nof_hits = int(request.GET['nof_hits']) if 'nof_hits' in request.GET else 100
    except ValueError:
        return JsonResponse({'error': 'invalid value for nof_hits'}, status=400)
    except Growing.DoesNotExist:
        return JsonResponse({'error': 'model not found'}, status=404)
    return JsonResponse(growing.dict(detail=detail, nof_hits=nof_hits), status=200, safe=False)


@csrf_exempt
def growing_download(request, growing_id):
    """Download a growing

    :param request: growing download request
    :param growing_id: growing id
    :type growing_id: int
    :return: zip file download or not found
    :rtype: HttpResponse
    """
    try:
        growing = Growing.objects.get(id=growing_id)
        zip_bytes = growing.write_zip_bytes()
        response = HttpResponse(zip_bytes.getvalue(), content_type='application/x-zip-compressed')
        response['Content-Length'] = len(response.content)
        response['Content-Disposition'] = f'attachment; filename="growing_{growing.id}.zip"'
        return response
    except Growing.DoesNotExist:
        return HttpResponse({'error': 'model not found'}, status=404)


def fragment_set_index(request):
    """Get an index of fragment sets

    :param request: fragment set indext request
    :return: list of fragment sets
    :rtype: JsonResponse
    """
    return JsonResponse(
        [fragment_set.dict() for fragment_set in FragmentSet.objects.all()],
        status=200,
        safe=False
    )
