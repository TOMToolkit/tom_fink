from django.test import tag, TestCase

from tom_fink.fink import FinkBroker
from tom_targets.models import Target


@tag('canary')
class TestFinkModuleCanary(TestCase):
    """NOTE: To run these tests in your venv: python ./tom_fink/tests/run_canary_tests.py"""

    def setUp(self):
        self.broker = FinkBroker()

    def test_boilerplate(self):
        self.assertTrue(True)
