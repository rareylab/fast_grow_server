"""fast_grow celery tasks"""
from celery import shared_task
from .tool_wrappers.preprocessor_wrapper import PreprocessorWrapper
from .models import Complex, Status


@shared_task
def preprocess_complex(complex_id):
    """preprocess a complex model using the preprocessor binary"""
    cmplx = Complex.objects.get(id=complex_id)
    try:
        PreprocessorWrapper.preprocess(cmplx)
        cmplx.status = Status.SUCCESS
        cmplx.save()
    except Exception as error:
        cmplx.status = Status.FAILURE
        cmplx.save()
        raise error
