"""fast_grow models"""
import json
import os
from tempfile import NamedTemporaryFile, TemporaryDirectory
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
        """Convert status to a readable string"""
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

        :return ensemble directory
        """
        directory = TemporaryDirectory()
        for protein in self.complex_set.all():
            protein.write_temp(temp_dir=directory.name)
        return directory

    def dict(self, detail=False):
        """Convert ensemble to dict

        :param detail create a detailed view of the ensemble (this can be quite large)
        :return ensemble_dict a dictionary containing members of the ensemble
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

        :param detail create a detailed view of the complex (this can be quite large)
        :return complex_dict a dictionary containing members of the complex in JSON friendly types
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

        :param temp_dir temp dir to write into
        :return complex_file
        """
        filename = self.name + '.' + self.file_type
        if temp_dir:
            temp_file = open(os.path.join(temp_dir, filename), 'w+')
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

        :param detail create a detailed view of the ligand (this can be quite large)
        :return ligand_dict a dictionary containing members of the ligand in JSON friendly types
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

        :return ligand_file
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
        """Convert interaction to a dictionary"""
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

        :param detail create a detailed view of the core (this can be quite large)
        :return core_dict a dictionary containing members of the core in JSON friendly types
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

    def write_temp(self):
        """Write a tempfile containing the core

        :return core_file
        """
        filename = self.name + '.' + self.file_type
        temp_file = NamedTemporaryFile(mode='w+', suffix=filename)
        temp_file.write(self.file_string)
        temp_file.seek(0)
        return temp_file


class FragmentSet(models.Model):
    """Model representing a fragment set"""
    name = models.CharField(max_length=255)

    def dict(self):
        """Convert fragment set to dict"""
        return {
            'id': self.id,
            'name': self.name
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

        :param detail create a detailed view of the growing (this can be quite large)
        :param nof_hits number of hits to extract from the database
        :return growing_dict a dictionary containing members of the growing in JSON friendly types
        """
        growing_dict = {
            'id': self.id,
            'complex': self.ensemble.dict(detail=detail),
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


class Hit(models.Model):
    """Model representing a hit of a growing"""
    growing = models.ForeignKey(Growing, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    score = models.FloatField()
    file_type = models.CharField(max_length=3)
    file_string = models.TextField()

    def dict(self):
        """Convert hit to dict"""
        return {
            'id': self.id,
            'name': self.name,
            'score': self.score,
            'file_type': self.file_type,
            'file_string': self.file_string
        }
