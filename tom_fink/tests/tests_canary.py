from django.test import tag, TestCase

from tom_fink.fink import FinkBroker


@tag('canary')
class TestFinkModuleCanary(TestCase):
    """NOTE: To run these tests in your venv: python ./tom_fink/tests/run_canary_tests.py"""

    def setUp(self):
        self.broker = FinkBroker()

    def test_boilerplate(self):
        self.assertTrue(True)


@tag('canary')
class TestFinkModuleSSOCanary(TestCase):
    """Tests for the Solar System Object (SSO) search functionality for Issue #98
    https://github.com/TOMToolkit/tom_fink/issues/98
    NOTE: To run these tests in your venv: python ./tom_fink/tests/run_canary_tests.py"""

    def setUp(self):
        self.broker = FinkBroker()
        self.parameters = {"query_name": "29P",
                           "broker": "Fink",
                           "objectId": "",
                           "conesearch": "",
                           "classsearch": "",
                           "classsearchdate": "",
                           "ssosearch": "29P"}

    def test_correctkeys(self):
        expected_keys = ['i:ssnamenr', 'i:candid', 'i:dec', 'i:jd', 'i:magpsf',
                         'i:objectId', 'i:ra', 'd:roid', 'sso_name', 'sso_number']
        data = self.broker.fetch_alerts(self.parameters)
        with self.assertRaises(StopIteration):
            while True:
                alert = next(data)
                for key in expected_keys:
                    self.assertTrue(key in alert.keys())
