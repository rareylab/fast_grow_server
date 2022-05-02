"""A django model friendly wrapper around the preprocessor binary"""
import logging
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from fast_grow.models import Ligand, Complex
from fast_grow.settings import PREPROCESSOR


class PreprocessorWrapper:
    """A django model friendly wrapper around the preprocessor binary"""

    @staticmethod
    def preprocess(ensemble):
        """Preprocess an ensemble using the preprocessor binary

        :param ensemble: django ensemble model to be preprocessed
        :type ensemble: fast_grow.models.Ensemble
        """
        with TemporaryDirectory() as output_directory:
            PreprocessorWrapper.execute_preprocessing(ensemble, output_directory)
            result_path = Path(output_directory)
            PreprocessorWrapper.load_results(result_path, ensemble)

    @staticmethod
    def execute_preprocessing(ensemble, output_directory):
        """Execute the preprocessor binary on the ensemble in the model

        If a ligand was explicitly specified it is considered in the commandline call.

        :param ensemble: django ensemble model to be preprocessed
        :type ensemble: fast_grow.models.Ensemble
        :param output_directory: directory to write output to
        :type output_directory: str
        """
        ligand_file = None
        if ensemble.ligand_set.count() == 1:
            ligand_file = ensemble.ligand_set.first().write_temp()
        elif ensemble.ligand_set.count() > 1:
            error_string = f'ensemble({ensemble.id}) to be processed has more than one ligand'
            raise RuntimeError(error_string)

        for cmplx in ensemble.complex_set.all():
            complex_file = cmplx.write_temp()
            cmplx.delete()
            # implicit zero case leaves ligand file at None
            args = [
                PREPROCESSOR,
                '--pocket', complex_file.name,
                '--outdir', output_directory,
            ]
            if ligand_file:
                args.extend(['--ligand', ligand_file.name])
            logging.debug(' '.join(args))
            subprocess.check_call(args)

    @staticmethod
    def load_results(path, ensemble):
        """Load all results into the database

        :param path: path to the results
        :type path: pathlib.Path
        :param ensemble: ensemble to load results into
        :type ensemble: fast_grow.models.Ensemble
        """
        PreprocessorWrapper.load_complexes(path, ensemble)
        if ensemble.ligand_set.count() == 1:
            # no need to load ligands
            return

        PreprocessorWrapper.load_ligands(path, ensemble)

    @staticmethod
    def load_complexes(path, ensemble):
        """Load all processed complexes

        :param path: path to the results
        :type path: pathlib.Path
        :param ensemble: ensemble to load results into
        :type ensemble: fast_grow.models.Ensemble
        """
        pdb_files = list(path.glob('*.pdb'))
        for pdb_file in pdb_files:
            with pdb_file.open() as complex_file:
                complex_string = complex_file.read()
            cmplx = Complex(
                ensemble=ensemble, name=pdb_file.stem, file_type='pdb', file_string=complex_string)
            cmplx.save()

    @staticmethod
    def load_ligands(path, ensemble):
        """Load all ligands extracted by the preprocessor binary

        :param path: path to the results
        :type path: pathlib.Path
        :param ensemble: ensemble to load results into
        :type ensemble: fast_grow.models.Ensemble
        """
        sd_files = list(path.glob('*.sdf'))
        for sd_file in sd_files:
            with sd_file.open() as ligand_file:
                ligand_string = ligand_file.read()
            ligand = Ligand(
                ensemble=ensemble, name=sd_file.stem, file_type='sdf', file_string=ligand_string)
            ligand.save()
