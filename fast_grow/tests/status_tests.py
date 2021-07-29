"""Status enum tests"""
from django.test import TestCase
from fast_grow.models import Status


class StatusTests(TestCase):
    """Status enum tests"""

    def test_to_string(self):
        """Test to string method of status enum"""
        self.assertEqual(Status.to_string(Status.PENDING), 'pending')
        self.assertEqual(Status.to_string(Status.RUNNING), 'running')
        self.assertEqual(Status.to_string(Status.SUCCESS), 'success')
        self.assertEqual(Status.to_string(Status.FAILURE), 'failure')
