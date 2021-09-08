"""fast_grow views"""
import os
import json
import re
import urllib.request
import urllib.error
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from fast_grow_server import settings
from .models import Complex, Core, FragmentSet, Growing, Ligand
from .tasks import preprocess_complex, clip_ligand, grow


@csrf_exempt
def complex_create(request):
    """Create a complex using file uploads or a pdb code

    If a ligand is uploaded as well, this ligand is associated with the complex. Schedules a celery
    job to preprocess the complex.
    """
    # this could be a decorator but I prefer the control
    if request.method != 'POST':
        return JsonResponse({'error': 'bad request'}, status=400)

    if 'pdb' in request.POST:
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
        )
    elif 'complex' in request.FILES:
        complex_filename, complex_extension = os.path.splitext(request.FILES['complex'].name)
        if complex_extension != '.pdb':
            return JsonResponse({'error': 'complex is not a PDB file (.pdb)'}, status=400)

        complex_name = os.path.basename(complex_filename)[:255]  # name has max size of 255
        complex_string = request.FILES['complex'].read().decode('utf8')
        cmplx = Complex(
            name=complex_name,
            file_type=complex_extension[1:],  # remove period at the beginning of the extension
            file_string=complex_string
        )
    else:
        return JsonResponse({'error': 'no complex specified'}, status=400)

    cmplx.save()
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
            complex=cmplx
        )
        ligand.save()
    preprocess_complex.delay(cmplx.id)
    return JsonResponse(cmplx.dict(), status=201, safe=False)


@csrf_exempt
def complex_detail(request, complex_id):
    """Get detailed information of a complex"""
    try:
        cmplx = Complex.objects.get(id=complex_id)
    except Complex.DoesNotExist:
        return JsonResponse({'error': 'model not found'}, status=404)
    return JsonResponse(cmplx.dict(detail=True), status=200, safe=False)


@csrf_exempt
def core_create(request):
    """Create a core using a ligand"""
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
    """Get detailed information of a core"""
    try:
        core = Core.objects.get(id=core_id)
    except Core.DoesNotExist:
        return JsonResponse({'error': 'model not found'}, status=404)
    return JsonResponse(core.dict(detail=True), status=200, safe=False)


@csrf_exempt
def growing_create(request):
    """Create a growing"""
    # this could be a decorator but I prefer the control
    if request.method != 'POST' or request.content_type != 'application/json':
        return JsonResponse({'error': 'bad request'}, status=400)
    try:
        request_json = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'bad request'}, status=400)

    if 'complex' not in request_json:
        return JsonResponse({'error': 'no complex specified'}, status=400)

    if 'core' not in request_json:
        return JsonResponse({'error': 'no core specified'}, status=400)

    if 'fragment_set' not in request_json:
        return JsonResponse({'error': 'no fragment set specified'}, status=400)

    try:
        cmplx = Complex.objects.get(id=int(request_json['complex']))
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
        complex=cmplx,
        core=core,
        fragment_set=fragment_set,
        search_points=json.dumps(search_points)
    )
    growing.save()
    grow.delay(growing.id)
    return JsonResponse(growing.dict(), status=201, safe=False)


@csrf_exempt
def growing_detail(request, growing_id):
    """Get detailed information of a growing"""
    try:
        growing = Growing.objects.get(id=growing_id)
        detail = request.GET['detail'] if 'detail' in request.GET else False
        nof_hits = int(request.GET['nof_hits']) if 'nof_hits' in request.GET else 100
    except ValueError:
        return JsonResponse({'error': 'invalid value for nof_hits'}, status=400)
    except Growing.DoesNotExist:
        return JsonResponse({'error': 'model not found'}, status=404)
    return JsonResponse(growing.dict(detail=detail, nof_hits=nof_hits), status=200, safe=False)
