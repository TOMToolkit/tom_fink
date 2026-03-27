from django.test import TestCase

from tom_dataservices.dataservices import QueryServiceError

from tom_fink.fink import FinkDataService


class TestFinkDataservice(TestCase):
    """NOTE: To run these tests in your venv: python ./tom_fink/tests/run_tests.py"""

    def setUp(self):
        self.fink_query = FinkDataService()

    def test_build_query_parameters_object(self):
        form_output = {
            'objectId': 'ZTF19acmdpyr',
            'conesearch': '',
            'classsearch': '',
            'classsearchdate': '',
            'ssosearch': ''}
        expected_query_parameters = {'objectId': 'ZTF19acmdpyr'}
        query_parameters = self.fink_query.build_query_parameters(form_output)
        self.assertEqual(query_parameters, expected_query_parameters)

    def test_build_query_parameters_multi_query(self):
        form_output = {
            'objectId': 'ZTF19acmdpyr',
            'conesearch': '12, 12, 5',
            'classsearch': '',
            'classsearchdate': '',
            'ssosearch': ''}
        with self.assertRaises(QueryServiceError):
            self.fink_query.build_query_parameters(form_output)

    def test_build_query_parameters_no_query(self):
        form_output = {
            'objectId': '',
            'conesearch': '',
            'classsearch': '',
            'classsearchdate': '',
            'ssosearch': ''}
        with self.assertRaises(QueryServiceError):
            self.fink_query.build_query_parameters(form_output)

    def test_build_query_parameters_bad_conesearch(self):
        form_output = {
            'objectId': '',
            'conesearch': '12, 12, 5, 12',
            'classsearch': '',
            'classsearchdate': '',
            'ssosearch': ''}
        with self.assertRaises(QueryServiceError):
            self.fink_query.build_query_parameters(form_output)

    def test_build_query_parameters_bad_conesearch2(self):
        form_output = {
            'objectId': '',
            'conesearch': '12, 12',
            'classsearch': '',
            'classsearchdate': '',
            'ssosearch': ''}
        with self.assertRaises(QueryServiceError):
            self.fink_query.build_query_parameters(form_output)

    def test_build_query_parameters_conesearch(self):
        form_output = {
            'objectId': '',
            'conesearch': '12, 12, 5',
            'classsearch': '',
            'classsearchdate': '',
            'ssosearch': ''}
        expected_query_parameters = {'objectId': '', 'ra': '12', 'dec': ' 12', 'radius': ' 5'}
        query_parameters = self.fink_query.build_query_parameters(form_output)
        self.assertEqual(query_parameters, expected_query_parameters)

    def test_build_query_parameters_class_num(self):
        form_output = {
            'objectId': '',
            'conesearch': '',
            'classsearch': 'AGN, 15',
            'classsearchdate': '',
            'ssosearch': ''}
        expected_query_parameters = {'objectId': '', 'class': 'AGN', 'n': ' 15'}
        query_parameters = self.fink_query.build_query_parameters(form_output)
        self.assertEqual(query_parameters, expected_query_parameters)

    def test_build_query_parameters_class_date(self):
        form_output = {
            'objectId': '',
            'conesearch': '',
            'classsearch': '',
            'classsearchdate': 'AGN, 15',
            'ssosearch': ''}
        expected_query_parameters = {'objectId': '', 'class': 'AGN'}
        query_parameters = self.fink_query.build_query_parameters(form_output)
        self.assertEqual(query_parameters['class'], expected_query_parameters['class'])
