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

from collections.abc import Iterator
import logging
from typing import Any, Dict, List

from django import forms

from tom_dataproducts.models import ReducedDatum
from tom_dataservices.dataservices import DataService
from tom_dataservices.forms import BaseQueryForm
from tom_fink import __version__ as fink_version
from tom_targets.models import Target

from astropy.time import Time
from crispy_forms.layout import Fieldset, HTML, Layout
import markdown as md
import numpy as np
import requests

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

FINK_URL = "https://fink-portal.org"
FINK_API_URL = "https://api.ztf.fink-portal.org"
COLUMNS = "i:candid,d:rf_snia_vs_nonia,i:ra,i:dec,i:jd,i:magpsf,i:objectId,d:cdsxmatch"
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
    ssosearch = forms.CharField(
        required=False,
        label="Solar System Objects Search",
        help_text=md.markdown(help_ssosearch),
        widget=forms.TextInput(attrs={"placeholder": "sso_name"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.layout = Layout(
            HTML(f"""
                <p>
                    <em>
                    TOM Toolkit Broker Module
                    (<a target="_blank" href="https://github.com/TOMToolkit/tom_fink">tom_fink</a>)
                    version {fink_version}
                    </em>
                </p>
                <p>
                    Please see the <a href="{FINK_API_URL}" target="_blank">Fink API homepage</a>
                    for a detailed description of this broker.
                </p>
            """),
            Fieldset(
                None,
                "objectId",
                "conesearch",
                "classsearchdate",
                "ssosearch",
            ),
        )


class FinkDataService(DataService):
    """
    This is an Example Data Service with the minimum required
    functionality.
    """
    name = 'Fink'

    @classmethod
    def get_form_class(cls):
        """
        Points to the form class discussed below.
        """
        return FinkServiceForm

    def build_query_parameters(self, parameters, **kwargs):
        """
        Use this function to convert the form results into the query parameters understood
        by the Data Service.
        """
        logger.debug(f'build_query_parameters -- parameters: {parameters}')

        # here, we're just passing the form data straight through to query_targets
        self.query_parameters = parameters
        return self.query_parameters

    def _fetch_alerts(self, parameters: dict) -> Iterator:
        """Call the Fink API based on parameters from the Query Form.

        Parameters
        ----------
        parameters: dict
            Dictionary that contains query parameters defined in the Form
            Example: {
                'query_name': 'toto',
                'broker': 'Fink',
                'objectId': 'ZTF19acnjwgm'
            }

        Returns
        -------
        out: iter
            Iterable on alert data (list of dictionary). Alert data is in
            the form {column name: value}.
        """
        allowed_search = [
            "objectId",
            "conesearch",
            "classsearch",  # at present, not in Form layout (above)
            "classsearchdate",
            "ssosearch",
        ]

        # first, check that one and only one search field is filled out
        nquery = np.sum([len(parameters[i].strip()) > 0 for i in allowed_search])
        if nquery > 1:
            msg = """
            You must fill only one query form at a time! Edit your query to choose
            only one query among: ZTF Object ID, Cone Search, Class Search, Solar System Objects Search
            """
            raise NotImplementedError(msg)
        elif nquery == 0:
            msg = """
            You must fill at least one query form! Edit your query to choose
            one query among: ZTF Object ID, Cone Search, Class Search, Solar System Objects Search
            """
            raise NotImplementedError(msg)

        if len(parameters["objectId"].strip()) > 0:
            # object search
            response = requests.post(
                FINK_API_URL + "/api/v1/objects",
                json={"objectId": parameters["objectId"].strip(), "columns": COLUMNS},
            )
        elif len(parameters["conesearch"].strip()) > 0:
            # cone search
            try:
                ra, dec, radius = parameters["conesearch"].split(",")
            except ValueError:
                raise
            response = requests.post(
                FINK_API_URL + "/api/v1/conesearch",
                json={"ra": ra, "dec": dec, "radius": radius},
            )
        elif len(parameters["classsearch"].strip()) > 0:
            # class search (at present, not in Form layout above)
            try:
                class_name, n_alert = parameters["classsearch"].split(",")
            except ValueError:
                raise
            response = requests.post(
                FINK_API_URL + "/api/v1/latests", json={"class": class_name, "n": n_alert}
            )
        elif len(parameters["classsearchdate"].strip()) > 0:
            # class search with n_day_in_past
            try:
                class_name, n_days_in_past = parameters["classsearchdate"].split(",")
            except ValueError:
                raise
            now = Time.now()
            start = Time(now.jd - float(n_days_in_past), format="jd").iso
            end = now.iso
            response = requests.post(
                FINK_API_URL + "/api/v1/latests",
                json={
                    "class": class_name,
                    "n": 1000,
                    "startdate": start,
                    "stopdate": end,
                },
            )
        elif len(parameters["ssosearch"].strip()) > 0:
            # SSO search
            response = requests.post(
                FINK_API_URL + "/api/v1/sso",
                json={"n_or_d": parameters["ssosearch"].strip(), "columns": SSO_COLUMNS},
            )
        else:
            msg = """
            You need to enter one of the query field! Choose among:
            search by ZTF objectId, conesearch, search by date, search by class,
            search by SSO name.
            """
            raise NotImplementedError(msg)

        response.raise_for_status()
        data = response.json()

        # turn the data iterable (container) into the alerts Iterator (stream)
        alerts: Iterator = iter(data)
        return alerts

    def query_service(self, query_parameters, **kwargs):  # type:ignore
        """
        This is where you actually make the call to the Data Service.
        Return the results.
        """
        logger.debug(f'query_service -- query_parameters: {query_parameters}')

        # _fetch_alerts is refactored from the original FinkBroker
        alerts = self._fetch_alerts(query_parameters)

        self.query_results = alerts
        return alerts

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
        # get an Iterator of alerts (not targets, not a list) in return
        query_results = self.query_service(query_parameters, **kwargs)

        # convert query_results: Iterator[Alert] to targets_from_query_result: Dict[target_name, alert]
        alerts_for_target: Dict[str, List[Dict[str, Any]]] = {}  # Dict[target_name, List[alert]]
        for ix, alert in enumerate(query_results):
            logger.debug(f'query_targets -- alerts[{ix}]: {alert}')
            target_name = alert['i:objectId']

            # get (or create) the list of alerts for this target_name
            alerts = alerts_for_target.get(target_name, [])
            alerts.append(alert)
            alerts_for_target[target_name] = alerts

        targets_for_selection_table = []
        for target_name, alerts in alerts_for_target.items():
            # each alert in the alerts: List[alert] may have slightly different values,
            # so derive value suitable for the table
            median_ra = float(np.median([alert['i:ra'] for alert in alerts]))
            median_dec = float(np.median([alert['i:dec'] for alert in alerts]))
            median_mag = float(np.median([alert['i:magpsf'] for alert in alerts]))
            jd_min = float(np.min([alert['i:jd'] for alert in alerts]))
            jd_max = float(np.max([alert['i:jd'] for alert in alerts]))
            # now create the dict whose fields appear in the Target table row for selection
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

        reduced_datums = []
        for alert in data:
            datum_value = alert  # include the raw alert items in the value dict
            datum_value['magnitude'] = alert['i:magpsf']  # and add the expected item(s)

            # convert 'i:jd' (Julian date) to timestamp
            timestamp = Time(alert['i:jd'], format='jd').to_datetime()

            reduced_datum, __ = ReducedDatum.objects.get_or_create(
                target=target,
                timestamp=timestamp,
                data_type=data_type,
                source_name='Fink',
                value=datum_value
            )
            reduced_datums.append(reduced_datum)
        return reduced_datums

    def create_target_from_query(self, target_result: Dict[str, Any], **kwargs) -> Target:
        """
        Create a Target from a selected individual alert. (target w/alert info)

        Selected Table to to Target object + reduced

        :param self: Description
        :param target_result: Dict of Target data for selected Target
        :type target_result: Dict[str, Any]
        :param kwargs: Description
        :return: Description

        :rtype: Target
        """
        # extract values from query target_result and create Target
        target, _ = Target.objects.get_or_create(
            name=target_result['name'],
            type='SIDEREAL',
            ra=target_result['ra'],
            dec=target_result['dec'],
        )

        return target
