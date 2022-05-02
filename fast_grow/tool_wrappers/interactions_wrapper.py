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
        :type search_point_data: fast_grow.models.SearchPointData
        """
        with TemporaryDirectory() as output_directory:
            InteractionWrapper.execute_generation(search_point_data, output_directory)
            data = InteractionWrapper.load_data(output_directory)
        search_point_data.data = json.dumps(data)

    @staticmethod
    def execute_generation(search_point_data, output_directory):
        """execute the interaction generation

        :param search_point_data: input data to generate interactions from
        :type search_point_data: fast_grow.models.SearchPointData
        :param output_directory: output directory to generate data into
        :type output_directory: str
        """
        ligand_file = search_point_data.ligand.write_temp()
        complex_file = search_point_data.complex.write_temp()
        args = [
            INTERACTIONS,
            '--pocket', complex_file.name,
            '--ligand', ligand_file.name,
            '--outdir', output_directory
        ]
        logging.debug(' '.join(args))
        subprocess.check_call(args)

    @staticmethod
    def load_data(output_directory):
        """load generated interaction data

        :param output_directory: directory the interactions were generated in
        :type output_directory: str
        :return: interaction data
        :rtype: dict
        """
        search_point_path = os.path.join(output_directory, 'search_points.json')
        if not os.path.exists(search_point_path):
            raise RuntimeError('Did not generate any search points')
        with open(search_point_path, encoding='utf8') as search_point_file:
            # parse JSON string to make sure it is valid
            data = json.load(search_point_file)
        return data
