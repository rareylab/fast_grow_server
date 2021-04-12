from celery import shared_task
from .models import Complex, Status
from .preprocessor_wrapper import PreprocessorWrapper


@shared_task
def preprocess_complex(complex_id):
    cmplx = Complex.objects.get(id=complex_id)
    try:
        PreprocessorWrapper.preprocess(cmplx)
        cmplx.status = Status.SUCCESS
        cmplx.save()
    except Exception as e:
        cmplx.status = Status.FAILURE
        cmplx.save()
        raise e
