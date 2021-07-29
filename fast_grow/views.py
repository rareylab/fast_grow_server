"""fast_grow views"""
import os
from datetime import datetime
import re
import urllib.request
import urllib.error
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from fast_grow_server import settings
from .models import Complex, Ligand
from .tasks import preprocess_complex


@csrf_exempt
def complex_create(request):
    """Create a complex using file uploads or a pdb code

    If a ligand is uploaded as well, this ligand is associated with the complex. Schedules a celery
    job to preprocess the complex.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'bad request'}, status=400)

    if 'complex' in request.FILES:
        complex_filename, complex_extension = os.path.splitext(request.FILES['complex'].name)
        if complex_extension != '.pdb':
            return JsonResponse({'error': 'complex is not a PDB file (.pdb)'}, status=400)

        complex_name = os.path.basename(complex_filename)[:255]  # name has max size of 255
        complex_string = request.FILES['complex'].read().decode('utf8')
        cmplx = Complex(
            name=complex_name,
            file_type=complex_extension[1:],  # remove period at the beginning of the extension
            file_string=complex_string,
            accessed=datetime.now()
        )
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
            accessed=datetime.now()
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
