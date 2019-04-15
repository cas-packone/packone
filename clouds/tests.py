import importlib
from django.test import TestCase
from clouds.models import Instance

class InstanceMethodTests(TestCase):
    def test_was_mismatch_instance_status_between_db_and_platform(self):
        pass