"""A django friendly wrapper around the clipper binary"""
import logging
import subprocess
from tempfile import NamedTemporaryFile
from fast_grow.settings import CLIPPER


class ClipperWrapper:
    """A django friendly wrapper around the clipper binary"""

    @staticmethod
    def clip(core):
        """clip a core using the clipper binary"""
        ligand = core.ligand
        ligand_file = ligand.write_temp()
        temp_file = NamedTemporaryFile(mode='w+', suffix='.' + ligand.file_type)
        args = [
            CLIPPER,
            '--ligand', ligand_file.name,
            '--clipped', temp_file.name,
            '--anchorposition', str(core.anchor),
            '--linkposition', str(core.linker)
        ]
        logging.debug(' '.join(args))
        subprocess.check_call(args)
        temp_file.seek(0)
        core.file_string = temp_file.read()
        core.file_type = ligand.file_type
