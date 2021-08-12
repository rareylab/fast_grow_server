"""fast_grow models"""
import json
from tempfile import NamedTemporaryFile
from django.db import models


class Status:  # pylint: disable=too-few-public-methods
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


class Complex(models.Model):
    """Model representing a protein complex"""
    name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=3)
    file_string = models.TextField()
    status = models.CharField(max_length=1, choices=Status.choices, default=Status.PENDING)
    accessed = models.DateField()

    def dict(self, detail=False):
        """Convert complex to dictionary

        :param detail create a detailed view of the complex (this can be quite large)
        :return complex_dict a dictionary containing members of the complex in JSON friendly types
        """
        complex_dict = {
            'id': self.id,
            'name': self.name,
            'status': Status.to_string(self.status)
        }
        if detail:
            complex_dict['file_type'] = self.file_type
            complex_dict['file_string'] = str(self.file_string)
            complex_dict['ligands'] = [ligand.dict() for ligand in self.ligand_set.all()]
            complex_dict['search_point_data'] = \
                [search_point_data.dict() for search_point_data in self.searchpointdata_set.all()]
        return complex_dict

    def write_temp(self):
        """Write a tempfile containing the complex

        :return complex_file
        """
        filename = self.name + '.' + self.file_type
        temp_file = NamedTemporaryFile(mode='w+', suffix=filename)
        temp_file.write(self.file_string)
        temp_file.seek(0)
        return temp_file


class Ligand(models.Model):
    """Model representing a ligand in a complex"""
    complex = models.ForeignKey(Complex, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=3)
    file_string = models.TextField()

    def dict(self):
        """Convert ligand to a dictionary"""
        return {
            'id': self.id,
            'complex_id': self.complex.id,
            'name': self.name,
            'file_type': self.file_type,
            'file_string': str(self.file_string)
        }

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
    data = models.TextField()

    def dict(self):
        """Convert interaction to a dictionary"""
        return {
            'id': self.id,
            'complex_id': self.complex.id,
            'ligand_id': self.ligand.id,
            'data': json.loads(self.data),
        }


class Core(models.Model):
    """Model representing a ligand core"""
    ligand = models.ForeignKey(Ligand, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    anchor = models.IntegerField()
    linker = models.IntegerField()
    file_type = models.CharField(max_length=3, null=True)
    file_string = models.TextField(null=True)
    status = models.CharField(max_length=1, choices=Status.choices, default=Status.PENDING)

    def dict(self):
        """Convert core to a dictionary"""
        core_dict = {
            'id': self.id,
            'ligand_id': self.ligand.id,
            'name': self.name,
            'anchor': self.anchor,
            'linker': self.linker,
            'status': Status.to_string(self.status)
        }
        if self.status == Status.SUCCESS:
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
