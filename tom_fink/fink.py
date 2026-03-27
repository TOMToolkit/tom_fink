# Copyright (c) 2021-2025 Julien Peloton
#
# This file is part of TOM Toolkit
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import logging
from typing import Any, Dict, List

from django import forms

from tom_dataproducts.models import ReducedDatum
from tom_dataservices.dataservices import DataService, QueryServiceError
from tom_dataservices.forms import BaseQueryForm
from tom_fink import __version__ as fink_version
from tom_targets.models import Target

from astropy.time import Time
from crispy_forms.layout import HTML, Layout
import markdown as md
import numpy as np
import requests

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

FINK_URL = "https://fink-broker.org/"
FINK_API_URL = "https://api.ztf.fink-portal.org"
FINK_REPO_URL = "https://github.com/TOMToolkit/tom_fink"
SSO_COLUMNS = "i:ssnamenr,i:candid,i:ra,i:dec,i:jd,i:magpsf,i:objectId,d:roid"


class FinkServiceForm(BaseQueryForm):
    """Class to organise the Query Form for Fink.

    It currently contains forms for
        * ObjectId search

    """

    help_objectid = """
    Enter a valid object ID to access its data, e.g. try:
    - ZTF19acmdpyr, ZTF19acnjwgm, ZTF17aaaabte, ZTF20abqehqf, ZTF18acuajcr
    This query will return all matching alerts.
    """
    objectId = forms.CharField(
        required=False,
        label="ZTF Object ID",
        widget=forms.TextInput(attrs={"placeholder": "enter a valid ZTF object ID"}),
        help_text=md.markdown(help_objectid),
    )

    help_conesearch = """
    Perform a conesearch around a position on the sky given by (RA, Dec, radius).
    The initializer for RA/Dec is very flexible and supports inputs provided in a number of convenient formats.
    The following ways of initializing a conesearch are all equivalent (radius in arcsecond):
    - 271.3914265, 45.2545134, 5
    - 271d23m29.135s, 45d15m16.25s, 5
    - 18h05m33.942s, +45d15m16.25s, 5
    - 18 05 33.942, +45 15 16.25, 5
    - 18:05:33.942, 45:15:16.25, 5
    Note that the maximum radius is 60 arcseconds. This query will return all matching objects (not individual alerts).
    """
    conesearch = forms.CharField(
        required=False,
        label="Cone Search",
        help_text=md.markdown(help_conesearch),
        widget=forms.TextInput(attrs={"placeholder": "RA, Dec, radius"}),
    )

    # ra = forms.CharField(
    #     required=False,
    #     label="RA",
    #     help_text=md.markdown(help_conesearch),
    # )

    # dec = forms.CharField(
    #     required=False,
    #     label="Dec",
    #     help_text=md.markdown(help_conesearch),
    # )

    # radius = forms.FloatField(
    #     required=False,
    #     label='Search Radius',
    #     help_text = "Maximum search radius of 60 arcseconds",
    #     widget=forms.TextInput(attrs={'placeholder': 'radius (arcseconds)'}),
    #     min_value=0.0,
    #     max_value=60,
    # )

    help_classsearch = f"""
    Choose a class of interest from {FINK_API_URL}/api/v1/classes
    to see the `n_alert` latest alerts processed by Fink. Example
    - Early SN candidate, 10
    - EB*, 10
    - AGN, 15
    - Solar System, 50
    """
    classsearch = forms.CharField(
        required=False,
        label="Class Search by number",
        help_text=md.markdown(help_classsearch),
        widget=forms.TextInput(attrs={"placeholder": "class, n_alert"}),
    )

    help_classsearchdate = f"""
    Choose a class of interest from {FINK_API_URL}/api/v1/classes
    to see the alerts processed by Fink in the last `n_days_in_past` days. Example
    - Early SN Ia the last day: Early SN candidate, 1
    - Early SN Ia the last 10 days: Early SN candidate, 10
    Note that n_days_in_past_max = 15.
    """
    classsearchdate = forms.CharField(
        required=False,
        label="Class Search by date",
        help_text=md.markdown(help_classsearchdate),
        widget=forms.TextInput(attrs={"placeholder": "class, n_days_in_past"}),
    )

    help_ssosearch = f"""
    The list of arguments for retrieving SSO data can be found at {FINK_API_URL}/api/v1/sso.
    The numbers or designations are taken from the MPC archive.
    When searching for a particular asteroid or comet, it is best to use the IAU number,
    as in 4209 for asteroid "4209 Briggs". You can also try for numbered comet (e.g. 10P),
    or interstellar object (none so far...). If the number does not yet exist, you can search for designation.
    Here are some examples of valid queries:

    * Asteroids by number (default)
      * Asteroids (Main Belt): 4209, 1922
      * Asteroids (Hungarians): 18582, 77799
      * Asteroids (Jupiter Trojans): 4501, 1583
      * Asteroids (Mars Crossers): 302530
    * Asteroids by designation (if number does not exist yet)
      * 2010JO69, 2017AD19, 2012XK111
    * Comets by number (default)
      * 10P, 249P, 124P
    * Comets by designation (if number does no exist yet)
      * C/2020V2, C/2020R2

    Note for designation, you can also use space (2010 JO69 or C/2020 V2).
    """
    # ssosearch = forms.CharField(
    #     required=False,
    #     label="Solar System Objects Search",
    #     help_text=md.markdown(help_ssosearch),
    #     widget=forms.TextInput(attrs={"placeholder": "sso_name"}),
    # )

    def get_layout(self):
        layout = Layout(
            HTML(f"""
                <p>
                    Please see the <a href="{FINK_API_URL}" target="_blank">Fink API homepage</a>
                    for a detailed description of this broker.
                </p>
            """),
            super().get_layout()
        )
        return layout

    def simple_fields(self):
        """Return List of fields to be included in the simple form."""
        return ['objectId']


class FinkDataService(DataService):
    """
    Fink Dataservice:
    Pulls in fink alerts for targets, creating a combined target with data based on each alert.
    """
    name = 'Fink'
    app_version = fink_version
    app_link = FINK_REPO_URL
    info_url = FINK_URL
    base_url = FINK_API_URL + '/api/v1/'

    @classmethod
    def get_form_class(cls):
        """
        Points to the form class.
        """
        return FinkServiceForm

    def build_query_parameters(self, form_output, **kwargs):
        """
        Use this function to convert the form results into the query parameters understood
        by query_service.
        """
        logger.debug(f'build_query_parameters -- parameters: {form_output}')

        allowed_search = [
            "objectId",
            "conesearch",
            "classsearch",
            "classsearchdate",
            # "ssosearch",  # Disabled until future updates
        ]

        # first, check that one and only one search field is filled out
        nquery = np.sum([len(form_output[i].strip()) > 0 for i in allowed_search])
        if nquery > 1:
            msg = """
            You must fill only one query form at a time! Edit your query to choose
            only one query among: ZTF Object ID, Cone Search, Class Search, Solar System Objects Search
            """
            raise QueryServiceError(msg)
        elif nquery == 0:
            msg = """
            You must fill at least one query form! Edit your query to choose
            one query among: ZTF Object ID, Cone Search, Class Search
            """
            raise QueryServiceError(msg)

        parameters = {'objectId': form_output["objectId"].strip(),
                      }
        try:
            if form_output["conesearch"].strip():
                parameters['ra'], parameters['dec'], parameters['radius'] = form_output["conesearch"].split(",")
            if form_output["classsearch"].strip():
                parameters['class'], parameters['n'] = form_output["classsearch"].split(",")
            if form_output["classsearchdate"].strip():
                parameters['class'], n_days_in_past = form_output["classsearchdate"].split(",")
                now = Time.now()
                parameters['start'] = Time(now.jd - float(n_days_in_past), format="jd").iso
                parameters['end'] = now.iso
        except ValueError as e:
            msg = f"""
            It's possible that you included the incorrect number of comma-separated values in the query field.</br>
            ({e})
            """
            raise QueryServiceError(msg)

        self.query_parameters = parameters
        return self.query_parameters

    def query_service(self, parameters, **kwargs):  # type:ignore
        """Call the Fink API based on parameters from the Query Form.

        Parameters
        ----------
        parameters: dict
            Dictionary that contains query parameters defined in the Form
            Possible key/combinations: [objectId], [ra, dec, radius], [class, n, (start, end)]

        Returns
        -------
        out: iter
            Iterable on alert data (list of dictionary). Alert data is in
            the form {column name: value}.
        """
        COLUMNS = "i:candid,d:rf_snia_vs_nonia,i:ra,i:dec,i:jd,i:fid,i:magpsf,i:objectId,d:cdsxmatch"

        if parameters.get("objectId"):
            # object search
            response = requests.post(
                self.base_url + "objects",
                json={"objectId": parameters["objectId"], "columns": COLUMNS}, timeout=60
            )
        elif parameters.get("ra") and parameters.get("dec") and parameters.get("radius"):
            # cone search
            response = requests.post(
                self.base_url + "conesearch",
                json={"ra": parameters['ra'], "dec": parameters['dec'], "radius": parameters['radius']},
            )
        elif parameters.get("class"):
            # class search (at present, not in Form layout above)
            json_dict = {"class": parameters['class'],
                         "n": parameters.get('n', 1000),
                         }
            if parameters.get('start') and parameters.get('end'):
                json_dict["startdate"] = parameters['start']
                json_dict["stopdate"] = parameters['end']
            response = requests.post(
                self.base_url + "latests", json=json_dict
            )
        # Remove SSO process until proper features added.
        # elif len(parameters["ssosearch"].strip()) > 0:
        #     # SSO search
        #     response = requests.post(
        #         FINK_API_URL + "/api/v1/sso",
        #         json={"n_or_d": parameters["ssosearch"].strip(), "columns": SSO_COLUMNS},
        #     )
        else:
            msg = """
            You need to enter one of the query field! Choose among:
            search by ZTF objectId, conesearch, search by date, search by class,
            search by SSO name.
            """
            raise QueryServiceError(msg)

        response.raise_for_status()
        data = response.json()

        self.query_results = data
        return data

    #
    # Targets
    #

    def query_targets(self, query_parameters, **kwargs) -> List[Dict[str, Any]]:
        """Return a List[Dict] of Target data. Each List element becomes a row in the
        selectable target create table. Each Dict item becomes a column in the table.

        :param query_parameters: The query_parameters returned by `build_query_parameters`
        :type query_parameters: Dict[str, str]

        Here's is an example of a single alert from an Object query
        alerts[0]: {
           'i:objectId': 'ZTF18abzktuy',
           'i:ra': 92.5117956
           'i:dec': 36.1095938,
           'i:jd': 2461051.7947569,
           'i:magpsf': 18.068764,
           'd:cdsxmatch': 'EclBin',
           'd:rf_snia_vs_nonia': 0.0,
           'i:candid': 3297294755815010006,
        }

        """
        logger.debug(f'query_targets -- query_parameters: {query_parameters}')

        # query Fink via query_service,
        query_results = self.query_service(query_parameters, **kwargs)
        logger.debug(f'query_targets -- query_results: {query_results}')

        # Reorganize the List[alert] into a target_name-keyed Dict of target-specific List[alert]
        # (i.e. convert query_results: List[Alert] to alerts_for_target: Dict[target_name, List[alert]])
        alerts_for_target: Dict[str, List[Dict[str, Any]]] = {}  # Dict[target_name, List[alert]]
        for alert in query_results:
            target_name = alert['i:objectId']  # will become dict key; value will be List[alert]

            alerts = alerts_for_target.get(target_name, [])  # get (or create) the list of alerts for this target_name
            alerts.append(alert)
            alerts_for_target[target_name] = alerts

        # Create the List of targets to be offered to the User for actual Target creation.
        targets_for_selection_table = []
        for target_name, alerts in alerts_for_target.items():
            # each alert in the alerts: List[alert] may have slightly different values,
            # so derive values suitable for the selection table
            median_ra = float(np.median([alert['i:ra'] for alert in alerts]))
            median_dec = float(np.median([alert['i:dec'] for alert in alerts]))
            median_mag = float(np.median([alert['i:magpsf'] for alert in alerts]))
            jd_min = float(np.min([alert['i:jd'] for alert in alerts]))
            jd_max = float(np.max([alert['i:jd'] for alert in alerts]))
            # now create the dict whose fields appear as columns in the Target selection table row
            target_table_row = {
                'name': target_name,
                'ra': median_ra,
                'dec': median_dec,
                'mag': median_mag,
                'jd_min': jd_min,
                'jd_max': jd_max,
                'num_alerts': len(alerts),
                'reduced_datums': {'photometry': alerts}
            }
            targets_for_selection_table.append(target_table_row)

        return targets_for_selection_table

    def create_target_from_query(self, target_result: Dict[str, Any], **kwargs) -> Target:
        """
        Create an unsaved Target from composite results built from selected relevant alerts.

        :param target_result: Dict of Target data for selected Target
        :type target_result: Dict[str, Any]

        :return: An unsaved Target instance. Create with constructor; DON'T use `get_or_create()`
        :rtype: Target
        """

        # extract values from query target_result and create Target
        # NOTE: use constructor, not get_or_create, the base `to_target` method will save the Target
        unsaved_target = Target(
            name=target_result['name'],
            type='SIDEREAL',
            ra=target_result['ra'],
            dec=target_result['dec'],
        )
        return unsaved_target

    def build_query_parameters_from_target(self, target, **kwargs) -> Dict[str, Any]:
        """
        This is a method that builds query parameters based on an existing target object that will be
        recognized by `query_service()`..

        In this particular case, we're looking for something that begins with ZTF: It could be the
        target name or it could be an alias.

        :param target: A target object to be queried
        :return: query_parameters (usually a dict) that can be understood by `query_service()`
        """
        # first, see if the target.name itself is a ZTF object ID.
        if target.name.startswith('ZTF'):
            objectId = target.name
        else:
            # if it's not,
            # search among the target's aliases for something that starts with 'ZTF'
            ztf_aliases = target.aliases.filter(name__startswith='ZTF').order_by('-created')
            if not ztf_aliases.exists():
                raise QueryServiceError(
                    f"Target '{target.name}' has neither name nor alias starting with 'ZTF'. "
                    f"Cannot build Fink query parameters."
                )
            if ztf_aliases.count() > 1:
                logger.warning(
                    f"Target '{target.name}' has multiple ZTF aliases: "
                    f"{list(ztf_aliases.values_list('name', flat=True))}. "
                    f"Using the most recent: '{ztf_aliases.first().name}'."
                )
            objectId = ztf_aliases.first().name  # use the most recent ZTF name found

        # construct query parameters with objectId
        query_parameters = {'objectId': objectId}
        logger.debug(f'build_query_parameters_from_target -- Target: {target}, query_parameters: {query_parameters}')
        return query_parameters

    #
    # Photometry
    #

    def query_photometry(self, query_parameters, **kwargs):
        """
        Query data service for photometry data

        Given the query_parameters, there should only be one Target among the Alerts
        (i.e. all the Alerts are for the same target (the one that was queried for).

        However, just to be sure, we re-organize the List[alert] into a target_name-keyed Dict of target-specific
        List[alert] (i.e. convert query_results: List[Alert] to alerts_for_target: Dict[target_name, List[alert]])
        """
        query_results = self.query_service(query_parameters, **kwargs)
        logger.debug(f'query_photometry -- query_results: {query_results}')

        alerts_for_target: Dict[str, List[Dict[str, Any]]] = {}  # Dict[target_name, List[alert]]
        for alert in query_results:
            target_name = alert['i:objectId']  # will become dict key; value will be List[alert]

            alerts = alerts_for_target.get(target_name, [])  # get (or create) the list of alerts for this target_name
            alerts.append(alert)
            alerts_for_target[target_name] = alerts

        # There should only one key,value pair in alert_for_target (i.e. only one target with it's alerts)
        if len(alerts_for_target.items()) != 1:
            raise QueryServiceError(f'Too many targets returned from {self.name}')

        return query_results

    def create_reduced_datums_from_query(self, target, data=None, data_type='photometry', **kwargs):
        """Create Photometry reduced_data instances from `data`. `data` is a List[alert]
        (the alerts returned by Fink).

        :param target: The Target these data pertain to.
        :type target: tom_targets.models.Target
        :param data: This is a list of alert dictionaries for the target. This is the
        reduced_datums['photometry'] List[alert] constructed in query_targets.
        :type data: List[Dict[str, Any]]

        """
        logger.debug(f'create_reduced_datums_from_query -- data:{type(data)} => {data}')
        if data is None:
            data = []

        reduced_datums = []
        for alert in data:
            datum_value = alert  # include the raw alert items in the value dict
            datum_value['magnitude'] = alert['i:magpsf']  # and add the expected item(s)
            datum_value['error'] = 0.0

            # convert filter ID to filter (1=g; 2=R; 3=i)
            filter_index = alert['i:fid'] - 1
            filter_names = ['g', 'R', 'i']
            datum_value['filter'] = filter_names[filter_index]

            # convert 'i:jd' (Julian date) to timestamp
            timestamp = Time(alert['i:jd'], format='jd').to_datetime()

            reduced_datum, _ = ReducedDatum.objects.get_or_create(
                target=target,
                timestamp=timestamp,
                data_type=data_type,
                source_name=self.name,
                value=datum_value
            )
            reduced_datums.append(reduced_datum)
        return reduced_datums
