"""fast_grow celery tasks"""
import logging
from celery import shared_task
from .tool_wrappers.preprocessor_wrapper import PreprocessorWrapper
from .tool_wrappers.clipper_wrapper import ClipperWrapper
from .tool_wrappers.fast_grow_wrapper import FastGrowWrapper
from .tool_wrappers.interactions_wrapper import InteractionWrapper
from .models import Ensemble, Core, SearchPointData, Status, Growing


@shared_task
def preprocess_ensemble(ensemble_id):
    """preprocess a complex model using the preprocessor binary"""
    ensemble = Ensemble.objects.get(id=ensemble_id)
    try:
        PreprocessorWrapper.preprocess(ensemble)
        ensemble.status = Status.SUCCESS
        ensemble.save()
    except Exception as error:
        logging.error(error)
        ensemble.status = Status.FAILURE
        ensemble.save()
        raise error


@shared_task
def clip_ligand(core_id):
    """clip a ligand into a core"""
    core = Core.objects.get(id=core_id)
    try:
        ClipperWrapper.clip(core)
        core.status = Status.SUCCESS
        core.save()
    except Exception as error:
        logging.error(error)
        core.status = Status.FAILURE
        core.save()
        raise error


@shared_task
def generate_interactions(search_point_id):
    """generate interactions search points for a ligand and complex"""
    search_point_data = SearchPointData.objects.get(id=search_point_id)
    try:
        InteractionWrapper.generate(search_point_data)
        search_point_data.status = Status.SUCCESS
        search_point_data.save()
    except Exception as error:
        logging.error(error)
        search_point_data.status = Status.FAILURE
        search_point_data.save()
        raise error


@shared_task
def grow(growing_id):
    """perform a growing"""
    growing = Growing.objects.get(id=growing_id)
    try:
        FastGrowWrapper.grow(growing)
        growing.status = Status.SUCCESS
        growing.save()
    except Exception as error:
        logging.error(error)
        growing.status = Status.FAILURE
        growing.save()
        raise error
