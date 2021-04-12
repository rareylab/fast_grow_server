import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from django.conf import settings
from .models import Ligand, Interaction


class PreprocessorWrapper:

    @staticmethod
    def preprocess(cmplx):
        directory = PreprocessorWrapper.execute_preprocessing(cmplx)
        result_path = Path(directory.name)
        PreprocessorWrapper.load_results(result_path, cmplx)

    @staticmethod
    def execute_preprocessing(cmplx):
        complex_file = cmplx.write_temp()
        ligand_file = None
        if cmplx.ligand_set.count() > 1:
            print(cmplx.ligand_set.count())
            raise RuntimeError('complex({}) to be processed has more than one ligand'.format(cmplx.id))
        elif cmplx.ligand_set.count() == 1:
            ligand_file = cmplx.ligand_set.first().write_temp()
        directory = TemporaryDirectory()
        args = [
            os.path.join(settings.BASE_DIR, 'bin', 'preprocessor'),
            '--pocket', complex_file.name,
            '--outdir', directory.name,
        ]
        if ligand_file:
            args.extend(['--ligand', ligand_file.name])
        subprocess.check_call(args)
        return directory

    @staticmethod
    def load_results(path, cmplx):
        PreprocessorWrapper.load_clean_complex(path, cmplx)
        if cmplx.ligand_set.count() == 1:
            ligands = [cmplx.ligand_set.first()]
        else:
            ligands = PreprocessorWrapper.load_ligands(path, cmplx)

        for ligand in ligands:
            interactions_path = path.joinpath(ligand.name + '_interactions.json')
            if interactions_path.exists():
                PreprocessorWrapper.load_interactions(interactions_path, cmplx, ligand)

            water_interactions_path = path.joinpath(ligand.name + '_water_interactions.json')
            if water_interactions_path.exists():
                PreprocessorWrapper.load_interactions(water_interactions_path, cmplx, ligand, water_interactions=True)

    @staticmethod
    def load_clean_complex(path, cmplx):
        pdb_files = list(path.glob('*.pdb'))
        if len(pdb_files) > 1:
            raise RuntimeError('found more than one pdb file in output')
        with pdb_files[0].open() as f:
            clean_complex_string = f.read()
        cmplx.file_string = clean_complex_string
        cmplx.save()

    @staticmethod
    def load_ligands(path, cmplx):
        ligands = []
        sd_files = list(path.glob('*.sdf'))
        for sd_file in sd_files:
            with sd_file.open() as f:
                ligand_string = f.read()
            ligand = Ligand(name=sd_file.stem, file_type='sdf', file_string=ligand_string, complex=cmplx)
            ligand.save()
            ligands.append(ligand)
        return ligands

    @staticmethod
    def load_interactions(path, cmplx, ligand, water_interactions=False):
        with open(path) as f:
            data = json.load(f)
        if 'interactions' not in data:
            return

        interactions = data['interactions']
        for interaction in interactions:
            interctn = Interaction(json_interaction=json.dumps(interaction), complex=cmplx, ligand=ligand,
                                   water_interaction=water_interactions)
            interctn.save()
