"""add_fragment_set command"""
from django.core.management.base import BaseCommand
from fast_grow.models import FragmentSet


class Command(BaseCommand):
    """add_fragment_set command"""
    help = 'Add a fragment set'

    def add_arguments(self, parser):
        parser.add_argument('fragment_set', type=str)

    def handle(self, *args, **options):
        fragment_set_name = options['fragment_set']
        fragment_set = FragmentSet(name=fragment_set_name)
        fragment_set.save()
