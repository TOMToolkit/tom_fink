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
import functools
import logging
from typing import Any, Dict, List
import warnings

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
FINK_REPO_URL = "https://github.com/TOMToolkit/tom_fink"
COLUMNS = "i:candid,d:rf_snia_vs_nonia,i:ra,i:dec,i:jd,i:fid,i:magpsf,i:objectId,d:cdsxmatch"
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
    app_version = fink_version
    app_link = FINK_REPO_URL

    @classmethod
    def get_form_class(cls):
        """
        Points to the form class discussed below.
        """
        return FinkServiceForm

    def get_simple_form_partial(self):
        """

        :param self: Description
        """
        return 'tom_fink/partials/fink_simple_form.html'

    def get_advanced_form_partial(self):
        """

        :param self: Description
        """
        return 'tom_fink/partials/fink_advanced_form.html'

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

        # NOTE: there's no benefit from creating an Iterator on the data:
        # it's already in memory and there's no lazy-loading here because
        # the data was already in the reponse

        return data

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
        Create a Target from a selected individual alert. (target w/alert info)

        Selected Table to to (unsaved) Target object + reduced

        :param self: Description
        :param target_result: Dict of Target data for selected Target
        :type target_result: Dict[str, Any]
        :param kwargs: Description

        :return: An unsaved Target instance. Create with constructor; DON'T use `get_or_create()`
        :rtype: Target
        """

        # extract values from query target_result and create Target
        # NOTE: use constructor, not get_or_create, CreateTargetFromQueryView will save the Target
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
        recognized by `query_service()`.

        This can be done by either by re-creating the form fields set by the Data Service Form and
        then calling `self.build_query_parameters()` with the results, or we can reproduce a limited
        set of parameters uniquely for a target query.

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
                raise ValueError(
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

        # construct query parameters with objectId filled in and all other search fields empty
        query_parameters = {
            'objectId': objectId,
            'conesearch': '',
            'classsearch': '',
            'classsearchdate': '',
            'ssosearch': '',
        }
        logger.debug(f'build_query_parameters_from_target -- Target: {target}, query_parameters: {query_parameters}')
        return query_parameters

    #
    # Photometry
    #

    def query_photometry(self, query_parameters, **kwargs):
        query_results = self.query_service(query_parameters, **kwargs)
        logger.debug(f'query_photometry -- query_results: {query_results}')

        # Given the query_parameters, there should only be one Target among the Alerts
        # (i.e. all the Alerts are for the same target (the one that was queried for).

        # However, just to be sure, we re-organize:

        # Reorganize the List[alert] into a target_name-keyed Dict of target-specific List[alert]
        # (i.e. convert query_results: List[Alert] to alerts_for_target: Dict[target_name, List[alert]])
        alerts_for_target: Dict[str, List[Dict[str, Any]]] = {}  # Dict[target_name, List[alert]]
        for alert in query_results:
            target_name = alert['i:objectId']  # will become dict key; value will be List[alert]

            alerts = alerts_for_target.get(target_name, [])  # get (or create) the list of alerts for this target_name
            alerts.append(alert)
            alerts_for_target[target_name] = alerts

        # There should only one key,value pair in alert_for_target (i.e. only one target with it's alerts)
        assert len(alerts_for_target.items()) == 1

        return query_results

    def create_reduced_datums_from_query(self, target, data=[], data_type='photometry', **kwargs):
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
                source_name='Fink',
                value=datum_value
            )
            reduced_datums.append(reduced_datum)
        return reduced_datums


def deprecated(message):
    def decorator(cls):
        orig_init = cls.__init__

        @functools.wraps(orig_init)
        def new_init(self, *args, **kwargs):
            warnings.warn(
                f"{cls.__name__} is deprecated. {message}",
                DeprecationWarning,
                stacklevel=2,  # skip over the __init__ and reference the caller
            )
            orig_init(self, *args, **kwargs)
        cls.__init__ = new_init
        return cls
    return decorator

from tom_alerts.alerts import GenericBroker, GenericAlert  # noqa


@deprecated("Use FinkDataService instead.")
class FinkBroker(GenericBroker):
    """
    The ``FinkBroker`` is the interface to the Fink alert broker.

    For information regarding Fink and its available
    filters for querying, please see http://134.158.75.151:24000/api
    """

    name = "Fink"
    form = FinkServiceForm

    def fetch_alerts(self, parameters: dict) -> iter:
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
        # Check the user fills only one query form
        allowed_search = [
            "objectId",
            "conesearch",
            "classsearch",
            "classsearchdate",
            "ssosearch",
        ]
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
            r = requests.post(
                FINK_API_URL + "/api/v1/objects",
                json={"objectId": parameters["objectId"].strip(), "columns": COLUMNS},
            )
        elif len(parameters["conesearch"].strip()) > 0:
            try:
                ra, dec, radius = parameters["conesearch"].split(",")
            except ValueError:
                raise
            r = requests.post(
                FINK_API_URL + "/api/v1/conesearch",
                json={"ra": ra, "dec": dec, "radius": radius},
            )
        elif len(parameters["classsearch"].strip()) > 0:
            try:
                class_name, n_alert = parameters["classsearch"].split(",")
            except ValueError:
                raise
            r = requests.post(
                FINK_API_URL + "/api/v1/latests", json={"class": class_name, "n": n_alert}
            )
        elif len(parameters["classsearchdate"].strip()) > 0:
            try:
                class_name, n_days_in_past = parameters["classsearchdate"].split(",")
            except ValueError:
                raise
            now = Time.now()
            start = Time(now.jd - float(n_days_in_past), format="jd").iso
            end = now.iso
            r = requests.post(
                FINK_API_URL + "/api/v1/latests",
                json={
                    "class": class_name,
                    "n": 1000,
                    "startdate": start,
                    "stopdate": end,
                },
            )
        elif len(parameters["ssosearch"].strip()) > 0:
            r = requests.post(
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

        r.raise_for_status()
        data = r.json()

        return iter(data)

    def fetch_alert(self, id: str):
        """Call the Fink API based on parameters from the Query Form.

        Parameters
        ----------
        parameters: str

        Returns
        -------
        out: iter
            Iterable on alert data (list of dictionary). Alert data is in
            the form {column name: value}.
        """
        r = requests.post(
            FINK_API_URL + "/api/v1/objects", json={"objectId": id, "columns": COLUMNS}
        )
        r.raise_for_status()
        data = r.json()
        return data

    def process_reduced_data(self, target, alert=None):
        pass

    def to_target(self, alert: dict) -> Target:
        """Redirect query result to a Target

        Parameters
        ----------
        alert: dict
            GenericAlert instance

        """
        target = Target.objects.create(
            name=alert.name,
            type="SIDEREAL",
            ra=alert.ra,
            dec=alert.dec,
        )
        return target

    def to_generic_alert(self, alert):
        """Extract relevant parameters from the Fink alert to the TOM interface

        Parameters
        ----------
        alert: dict
            Dictionary containing alert data: {column name: value}. See
            `self.fetch_alerts` for more information.

        Returns
        -------
        out: GenericAlert
            Alert columns to be displayed on the TOM interface
        """
        # This URL points to the objectId page in the Fink Science Portal
        url = "{}/{}".format(FINK_URL, alert["i:objectId"])

        return GenericAlert(
            timestamp=alert["i:jd"],
            id=alert["i:candid"],
            url=url,
            name=alert["i:objectId"],
            ra=alert["i:ra"],
            dec=alert["i:dec"],
            mag=alert["i:magpsf"],
            score=alert.get("d:rf_snia_vs_nonia", 0),
        )
