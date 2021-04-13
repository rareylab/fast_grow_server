"""fast_grow views"""
import os
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Complex, Ligand
from .tasks import preprocess_complex


@csrf_exempt
def complex_create(request):
    """Create a complex using file uploads

    If a ligand is uploaded as well, this ligand is associated with the complex. Schedules a celery
    job to preprocess the complex.
    """
    if request.method == 'POST':
        if 'complex' in request.FILES:
            complex_filename, complex_extension = os.path.splitext(request.FILES['complex'].name)
            if complex_extension != '.pdb':
                return JsonResponse({'error': 'complex is not a PDB file (.pdb)'}, status=400)

            complex_name = os.path.basename(complex_filename)[:255]  # name has max size of 255
            complex_string = request.FILES['complex'].read().decode('utf8')
            cmplx = Complex(
                name=complex_name,
                file_type=complex_extension[1:],  # remove period
                file_string=complex_string,
                accessed=datetime.now()
            )
            cmplx.save()
            if 'ligand' in request.FILES:
                ligand_filename, ligand_extension = os.path.splitext(request.FILES['ligand'].name)
                if ligand_extension != '.sdf':
                    return JsonResponse({'error': 'ligand is not an SD file (.sdf)'}, status=400)

                ligand_name = os.path.basename(ligand_filename)[:255]  # name has max size of 255
                ligand_string = request.FILES['ligand'].read()
                ligand = Ligand(
                    name=ligand_name,
                    file_type=ligand_extension[1:],  # remove period
                    file_string=ligand_string,
                    complex_id=cmplx
                )
                ligand.save()
            preprocess_complex.delay(cmplx.id)
            return JsonResponse(cmplx.dict(), status=201, safe=False)
        return JsonResponse({'error': 'no complex specified'}, status=400)
    return JsonResponse({'error': 'bad request'}, status=400)


@csrf_exempt
def complex_detail(request, complex_id):
    """Get detailed information of a complex"""
    try:
        cmplx = Complex.objects.get(id=complex_id)
    except Complex.DoesNotExist:
        return JsonResponse({'error': 'model not found'}, status=404)
    return JsonResponse(cmplx.dict(detail=True), status=200, safe=False)
