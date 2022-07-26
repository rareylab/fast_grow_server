"""fast_grow models"""
import json
import os
from io import BytesIO
from tempfile import NamedTemporaryFile, TemporaryDirectory
from zipfile import ZipFile
from django.db import models


class Status:
    """Class wrapping a status enum"""
    PENDING = 'p'
    RUNNING = 'r'
    SUCCESS = 's'
    FAILURE = 'f'

    choices = [
        (PENDING, 'pending'),
        (RUNNING, 'running'),
        (SUCCESS, 'success'),
        (FAILURE, 'failure'),
    ]

    @staticmethod
    def to_string(status):
        """Convert status to a readable string

        :param status: status char to convert
        :type status: str
        :return: status string
        :rtype: str
        """
        if status == 'p':
            return 'pending'
        if status == 'r':
            return 'running'
        if status == 's':
            return 'success'
        if status == 'f':
            return 'failure'
        return None


class Ensemble(models.Model):
    """Model representing a complex ensemble"""
    accessed = models.DateField(auto_now=True)
    # status of the job that will preprocess the complex
    status = models.CharField(max_length=1, choices=Status.choices, default=Status.PENDING)

    def write_temp(self):
        """Write a temp directory containing the ensemble

        :return: ensemble directory
        :rtype: TemporaryDirectory
        """
        directory = TemporaryDirectory()
        self.write(directory.name)
        return directory

    def write(self, path):
        """Write ensemble proteins to path"""
        for protein in self.complex_set.all():
            protein.write_temp(temp_dir=path)

    def dict(self, detail=False):
        """Convert ensemble to dict

        :param detail: create a detailed view of the ensemble (this can be quite large)
        :type detail: bool
        :return: a dictionary containing members of the ensemble
        :rtype: dict
        """
        ensemble_dict = {
            'id': self.id,
            'complexes': [cmplx.dict(detail=detail) for cmplx in self.complex_set.all()],
            'ligands': [ligand.dict(detail=detail) for ligand in self.ligand_set.all()],
            'status': Status.to_string(self.status)
        }
        return ensemble_dict


class Complex(models.Model):
    """Model representing a protein complex"""
    ensemble = models.ForeignKey(Ensemble, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=3, null=True)
    file_string = models.TextField(null=True)

    def dict(self, detail=False):
        """Convert complex to dictionary

        :param detail: create a detailed view of the complex (this can be quite large)
        :type detail: bool
        :return: a dictionary containing members of the complex in JSON friendly types
        :rtype: dict
        """
        complex_dict = {
            'id': self.id,
            'name': self.name
        }
        if detail:
            complex_dict['file_type'] = self.file_type
            complex_dict['file_string'] = str(self.file_string)
        return complex_dict

    def write_temp(self, temp_dir=None):
        """Write a tempfile containing the complex

        Instead of writing a temp file pass a temp dir and write a real file into it. Cleanup of the
        this file is left up to the cleanup of the temp dir.

        :param temp_dir: temp dir to write into
        :type temp_dir: TemporaryDirectory
        :return: complex file
        :rtype: File
        """
        filename = self.name + '.' + self.file_type
        if temp_dir:
            temp_file = open(os.path.join(temp_dir, filename), 'w+', encoding='utf8')
        else:
            temp_file = NamedTemporaryFile(mode='w+', suffix=filename)
        temp_file.write(self.file_string)
        temp_file.seek(0)
        return temp_file


class Ligand(models.Model):
    """Model representing a ligand in a complex"""
    ensemble = models.ForeignKey(Ensemble, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=3)
    file_string = models.TextField()

    def dict(self, detail=False):
        """Convert ligand to a dictionary

        :param detail: create a detailed view of the ligand (this can be quite large)
        :type detail: bool
        :return: a dictionary containing members of the ligand in JSON friendly types
        :rtype: dict
        """
        ligand_dict = {
            'id': self.id,
            'ensemble_id': self.ensemble.id,
            'name': self.name
        }
        if detail:
            ligand_dict['file_type'] = self.file_type
            ligand_dict['file_string'] = self.file_string
        return ligand_dict

    def write_temp(self):
        """Write a tempfile containing the ligand

        :return: ligand file
        :rtype: NamedTemporaryFile
        """
        filename = self.name + '.' + self.file_type
        temp_file = NamedTemporaryFile(mode='w+', suffix=filename)
        temp_file.write(self.file_string)
        temp_file.seek(0)
        return temp_file


class SearchPointData(models.Model):
    """Model representing a protein-ligand interaction"""
    complex = models.ForeignKey(Complex, on_delete=models.CASCADE)
    ligand = models.ForeignKey(Ligand, on_delete=models.CASCADE)
    data = models.TextField(null=True)
    status = models.CharField(max_length=1, choices=Status.choices, default=Status.PENDING)

    def dict(self, detail=False):
        """Convert interaction to a dictionary

        :param detail: create a detailed view of the search point data (this can be quite large)
        :type detail: bool
        :return: a dictionary containing members of the ligand in JSON friendly types
        :rtype: dict
        """
        search_point_dict = {
            'id': self.id,
            'complex_id': self.complex.id,
            'ligand_id': self.ligand.id,
            'status': Status.to_string(self.status)
        }
        if detail:
            search_point_dict['data'] = json.loads(self.data) if self.data else None
        return search_point_dict


class Core(models.Model):
    """Model representing a ligand core"""
    ligand = models.ForeignKey(Ligand, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    anchor = models.IntegerField()
    linker = models.IntegerField()
    file_type = models.CharField(max_length=3, null=True)
    file_string = models.TextField(null=True)
    # status of the job that will execute the core generation
    status = models.CharField(max_length=1, choices=Status.choices, default=Status.PENDING)

    def dict(self, detail=False):
        """Convert core to a dictionary

        :param detail: create a detailed view of the core (this can be quite large)
        :type detail: bool
        :return: a dictionary containing members of the core in JSON friendly types
        :rtype: dict
        """
        core_dict = {
            'id': self.id,
            'ligand_id': self.ligand.id,
            'name': self.name,
            'anchor': self.anchor,
            'linker': self.linker,
            'status': Status.to_string(self.status)
        }
        if detail and self.status == Status.SUCCESS:
            core_dict['file_type'] = self.file_type
            core_dict['file_string'] = self.file_string
        return core_dict

    def write_temp(self, path=None):
        """Write a tempfile containing the core

        :param path: path to a dir to write into
        :type path: str
        :return: core file
        :rtype: File
        """
        filename = self.name + '.' + self.file_type
        if not path:
            core_file = NamedTemporaryFile(mode='w+', suffix=filename)
        else:
            core_file = open(os.path.join(path, filename), 'w', encoding='utf8')
        core_file.write(self.file_string)
        core_file.seek(0)
        return core_file


class FragmentSet(models.Model):
    """Model representing a fragment set"""
    name = models.CharField(max_length=255)
    description = models.TextField(null=True)

    def dict(self):
        """Convert fragment set to dict

        :return: a dictionary containing members of the fragment set in JSON friendly types
        :rtype: dict
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }


class Growing(models.Model):
    """Model representing a growing"""
    ensemble = models.ForeignKey(Ensemble, on_delete=models.CASCADE)
    core = models.ForeignKey(Core, on_delete=models.CASCADE)
    fragment_set = models.ForeignKey(FragmentSet, on_delete=models.CASCADE)
    search_points = models.TextField(null=True)
    # status of the job that will execute the growing
    status = models.CharField(max_length=1, choices=Status.choices, default=Status.PENDING)

    def dict(self, detail=False, nof_hits=100):
        """Convert growing to dict

        :param detail: create a detailed view of the growing (this can be quite large)
        :type detail: bool
        :param nof_hits: number of hits to extract from the database
        :type nof_hits: int
        :return: a dictionary containing members of the growing in JSON friendly types
        :rtype: dict
        """
        growing_dict = {
            'id': self.id,
            'ensemble': self.ensemble.dict(detail=detail),
            'core': self.core.dict(detail=detail),
            'fragment_set': self.fragment_set.name,
            'search_points': json.loads(self.search_points) if self.search_points else None,
            'status': Status.to_string(self.status)
        }
        if self.hit_set.count() and nof_hits:
            growing_dict['hits'] = [h.dict() for h in self.hit_set.order_by('score')[:nof_hits]]
        elif self.hit_set.count():
            growing_dict['hits'] = [h.dict() for h in self.hit_set.order_by('score').all()]
        return growing_dict

    def write_zip_bytes(self):
        """Serialize the contents of the growing into ZIP bytes

        :return: zip bytes
        :rtype: BytesIO
        """
        with TemporaryDirectory() as temp_dir:
            zip_bytes = BytesIO()
            zip_file = ZipFile(zip_bytes, 'w')
            ensemble_path = os.path.join(temp_dir, 'ensemble')
            os.mkdir(ensemble_path)

            self.ensemble.write(path=ensemble_path)
            for protein in os.listdir(ensemble_path):
                zip_file.write(
                    os.path.join(ensemble_path, protein),
                    os.path.join('growing', 'ensemble', protein)
                )

            core_file = self.core.write_temp(path=temp_dir)
            zip_file.write(
                core_file.name,
                os.path.join('growing', os.path.basename(core_file.name))
            )

            if self.search_points:
                search_point_path = os.path.join(temp_dir, 'search_points.json')
                with open(search_point_path, 'w', encoding='utf8') as search_point_file:
                    json.dump(self.search_points, search_point_file)
                zip_file.write(
                    search_point_file.name,
                    os.path.join('growing', os.path.basename(search_point_path)))

            if self.hit_set.count() > 0:
                hits_path = os.path.join(temp_dir, 'hits.sdf')
                with open(hits_path, 'w', encoding='utf8') as hits_file:
                    for hit in self.hit_set.all():
                        hits_file.write(hit.file_string)
                zip_file.write(hits_path, os.path.join('growing', 'hits.sdf'))
        return zip_bytes


class Hit(models.Model):
    """Model representing a hit of a growing"""
    growing = models.ForeignKey(Growing, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    score = models.FloatField()
    ensemble_scores = models.JSONField()
    file_type = models.CharField(max_length=3)
    file_string = models.TextField()

    def dict(self):
        """Convert hit to dict

        :return: a dictionary containing members of the hit in JSON friendly types
        :rtype: dict
        """
        return {
            'id': self.id,
            'name': self.name,
            'score': self.score,
            'file_type': self.file_type,
            'file_string': self.file_string,
            'ensemble_scores': self.ensemble_scores
        }
