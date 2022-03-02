"""A django friendly wrapper around the interaction generator binary"""
import json
import logging
import os.path
import subprocess

from tempfile import TemporaryDirectory
from fast_grow.settings import INTERACTIONS


class InteractionWrapper:
    """A django friendly wrapper around the interaction generator binary"""

    @staticmethod
    def generate(search_point_data):
        """generate interaction data

        :param search_point_data: input data to generate interactions from
        """
        output_directory = InteractionWrapper.execute_generation(search_point_data)
        data = InteractionWrapper.load_data(output_directory)
        search_point_data.data = json.dumps(data)

    @staticmethod
    def execute_generation(search_point_data):
        """execute the interaction generation

        :param search_point_data: input data to generate interactions from
        :return: directory the interactions were generated in
        """
        directory = TemporaryDirectory()
        ligand_file = search_point_data.ligand.write_temp()
        complex_file = search_point_data.complex.write_temp()
        args = [
            INTERACTIONS,
            '--pocket', complex_file.name,
            '--ligand', ligand_file.name,
            '--outdir', directory.name
        ]
        logging.debug(' '.join(args))
        subprocess.check_call(args)
        return directory

    @staticmethod
    def load_data(output_directory):
        """load generated interaction data

        :param output_directory: directory the interactions were generated in
        :return: interaction data
        """
        search_point_path = os.path.join(output_directory.name, 'search_points.json')
        if not os.path.exists(search_point_path):
            raise RuntimeError('Did not generate any search points')
        with open(search_point_path) as search_point_file:
            # parse JSON string to make sure it is valid
            data = json.load(search_point_file)
        return data
