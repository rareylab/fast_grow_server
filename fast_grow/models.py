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
            complex_dict['interactions'] = \
                [interactions.dict() for interactions in self.interaction_set.all()]
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


class Interaction(models.Model):
    """Model representing a protein-ligand interaction"""
    complex = models.ForeignKey(Complex, on_delete=models.CASCADE)
    ligand = models.ForeignKey(Ligand, on_delete=models.CASCADE)
    json_interaction = models.TextField()
    water_interaction = models.BooleanField(default=False)

    def dict(self):
        """Convert interaction to a dictionary"""
        return {
            'id': self.id,
            'complex_id': self.complex.id,
            'ligand_id': self.ligand.id,
            'interactions': json.loads(self.json_interaction),
            'water_interaction': self.water_interaction
        }
