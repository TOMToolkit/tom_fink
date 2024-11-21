from django.test import TestCase
from tom_fink.fink import FinkBroker
# from tom_fink.fink import FinkQueryForm, FinkBroker

test_alert1 =  {
    "i:candid": 1333145050315015017,
    "i:dec": 36.89327,
    "i:objectId": "ZTF18aaavxvj",
    "i:publisher": "Fink",
    "i:ra": 273.8834457,
    "v:classification": "RRLyr",
    "v:lastdate": "2020-08-26 03:28:53.003",
    "v:firstdate": "2018-02-07 12:46:49.996",
 }

test_alert2 =  {
    "i:candid": 1333145050315015017,
    "i:dec": 36.89327,
    "i:objectId": "ZTF18aaavxvj",
    "i:publisher": "Fink",
    "i:ra": 273.8834457,
    "v:classification": "RRLyr",
    "v:lastdate": "2020-08-26 03:28:53.003 UTC",
    "v:firstdate": "2018-02-07 12:46:49.996 UTC",
 }

class TestFinkQueryForm(TestCase):
    """
    NOTE: to run these tests in your venv: python ./tom_fink/tests/run_tests.py
    """
    def setUp(self):
        pass

    def test_boilerplate(self):
        """Make sure the testing infrastructure is working."""
        self.assertTrue(True)




class TestFinkBrokerClass(TestCase):
    """NOTE: To run these tests in your venv: python ./tom_fink/tests/run_tests.py"""

    def setUp(self):
        self.test_data = test_alert1
        self.expected_alert = test_alert2

    def test_clean_date(self):
        test_alert = self.test_data
        new_alert = FinkBroker()._clean_date(self, test_alert)
        self.assertEqual(test_alert, new_alert)



