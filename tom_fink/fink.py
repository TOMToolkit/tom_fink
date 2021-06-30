# Copyright (c) 2021 Julien Peloton
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
from tom_alerts.alerts import GenericAlert, GenericBroker, GenericQueryForm
from tom_targets.models import Target

from django import forms
import requests
import markdown as md
import numpy as np
from astropy.time import Time

FINK_URL = "http://134.158.75.151:24000"
COLUMNS = 'i:candid,d:rfscore,i:ra,i:dec,i:jd,i:magpsf,i:objectId,d:cdsxmatch'


class FinkQueryForm(GenericQueryForm):
    """ Class to organise the Query Form for Fink.

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
        label='ZTF Object ID',
        widget=forms.TextInput(
            attrs={'placeholder': 'enter a valid ZTF object ID'}
        ),
        help_text=md.markdown(
            help_objectid
        ),
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
        label='Cone Search',
        help_text=md.markdown(
            help_conesearch
        ),
        widget=forms.TextInput(
            attrs={
                'placeholder': 'RA, Dec, radius'
            }
        )
    )

    help_datesearch = """
    Choose a starting date and a time window to see all processed alerts in this period.
    Dates are in UTC, and the time window in minutes.
    Among several, you can choose YYYY-MM-DD hh:mm:ss, Julian Date, or Modified Julian Date.
    Example of valid search with a window of 2 minutes:
    - 2019-11-03 02:40:00, 2
    - 2458790.61111, 2
    - 58790.11111, 2
    Maximum window is 180 minutes (query can be very long!). This query will return all matching objects (not individual
    alerts).
    """
    datesearch = forms.CharField(
        required=False,
        label='Date Search',
        help_text=md.markdown(
            help_datesearch
        ),
        widget=forms.TextInput(
            attrs={
                'placeholder': 'startdate, window'
            }
        )
    )

    help_classsearch = """
    Choose a class of interest from {}/api/v1/classes
    to see the `n_alert` latest alerts processed by Fink. Example
    - Early SN candidate, 10
    - EB*, 10
    - AGN, 15
    - Solar System, 50
    """.format(FINK_URL)
    classsearch = forms.CharField(
        required=False,
        label='Class Search by number',
        help_text=md.markdown(
            help_classsearch
        ),
        widget=forms.TextInput(
            attrs={
                'placeholder': 'class, n_alert'
            }
        )
    )

    help_classsearchdate = """
    Choose a class of interest from {}/api/v1/classes
    to see the alerts processed by Fink in the last `n_days_in_past` days. Example
    - Early SN Ia the last day: Early SN candidate, 1
    - Early SN Ia the last 10 days: Early SN candidate, 10
    Note that n_days_in_past_max = 15.
    """.format(FINK_URL)
    classsearchdate = forms.CharField(
        required=False,
        label='Class Search by date',
        help_text=md.markdown(
            help_classsearchdate
        ),
        widget=forms.TextInput(
            attrs={
                'placeholder': 'class, n_days_in_past'
            }
        )
    )

    help_ssosearch = """
    The list of arguments for retrieving SSO data can be found at {}/api/v1/sso.
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
    """.format(FINK_URL)
    ssosearch = forms.CharField(
        required=False,
        label='Solar System Objects Search',
        help_text=md.markdown(
            help_ssosearch
        ),
        widget=forms.TextInput(
            attrs={
                'placeholder': 'sso_name'
            }
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class FinkBroker(GenericBroker):
    """
    The ``FinkBroker`` is the interface to the Fink alert broker.

    For information regarding Fink and its available
    filters for querying, please see http://134.158.75.151:24000/api
    """

    name = 'Fink'
    form = FinkQueryForm

    def fetch_alerts(self, parameters: dict) -> iter:
        """ Call the Fink API based on parameters from the Query Form.

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
        ----------
        out: iter
            Iterable on alert data (list of dictionary). Alert data is in
            the form {column name: value}.
        """
        # Check the user fills only one query form
        allowed_search = [
            'objectId', 'conesearch', 'datesearch',
            'classsearch', 'classsearchdate', 'ssosearch'
        ]
        nquery = np.sum([len(parameters[i].strip()) > 0 for i in allowed_search])
        if nquery > 1:
            msg = """
            You must fill only one query form at a time! Edit your query to choose
            only one query among: ZTF Object ID, Cone Search, Date Search, Class Search, Solar System Objects Search
            """
            raise NotImplementedError(msg)
        elif nquery == 0:
            msg = """
            You must fill at least one query form! Edit your query to choose
            one query among: ZTF Object ID, Cone Search, Date Search, Class Search, Solar System Objects Search
            """
            raise NotImplementedError(msg)

        if len(parameters['objectId'].strip()) > 0:
            r = requests.post(
                FINK_URL + '/api/v1/objects',
                json={
                    'objectId': parameters['objectId'].strip(),
                    'columns': COLUMNS
                }
            )
        elif len(parameters['conesearch'].strip()) > 0:
            try:
                ra, dec, radius = parameters['conesearch'].split(',')
            except ValueError:
                raise
            r = requests.post(
                FINK_URL + '/api/v1/explorer',
                json={
                    'ra': ra,
                    'dec': dec,
                    'radius': radius
                }
            )
        elif len(parameters['datesearch'].strip()) > 0:
            try:
                startdate, window = parameters['datesearch'].split(',')
            except ValueError:
                raise
            r = requests.post(
                FINK_URL + '/api/v1/explorer',
                json={
                    'startdate': startdate,
                    'window': window
                }
            )
        elif len(parameters['classsearch'].strip()) > 0:
            try:
                class_name, n_alert = parameters['classsearch'].split(',')
            except ValueError:
                raise
            r = requests.post(
                FINK_URL + '/api/v1/latests',
                json={
                    'class': class_name,
                    'n': n_alert
                }
            )
        elif len(parameters['classsearchdate'].strip()) > 0:
            try:
                class_name, n_days_in_past = parameters['classsearchdate'].split(',')
            except ValueError:
                raise
            now = Time.now()
            start = Time(now.jd - float(n_days_in_past), format='jd').iso
            end = now.iso
            r = requests.post(
                FINK_URL + '/api/v1/latests',
                json={
                    'class': class_name,
                    'n': 1000,
                    'startdate': start,
                    'stopdate': end
                }
            )
        elif len(parameters['ssosearch'].strip()) > 0:
            r = requests.post(
                FINK_URL + '/api/v1/sso',
                json={
                    'n_or_d': parameters['ssosearch'].strip(),
                    'columns': COLUMNS
                }
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
        """ Call the Fink API based on parameters from the Query Form.

        Parameters
        ----------
        parameters: str

        Returns
        ----------
        out: iter
            Iterable on alert data (list of dictionary). Alert data is in
            the form {column name: value}.
        """
        r = requests.post(
            FINK_URL + '/api/v1/explorer',
            json={
                'objectId': id,
                'columns': COLUMNS
            }
        )
        r.raise_for_status()
        data = r.json()
        return data

    def process_reduced_data(self, target, alert=None):
        pass

    def to_target(self, alert: dict) -> Target:
        """ Redirect query result to a Target

        Parameters
        ----------
        alert: dict
            GenericAlert instance

        """
        target = Target.objects.create(
            name=alert.name,
            type='SIDEREAL',
            ra=alert.ra,
            dec=alert.dec,
        )
        return target

    def to_generic_alert(self, alert):
        """ Extract relevant parameters from the Fink alert to the TOM interface

        Parameters
        ----------
        alert: dict
            Dictionary containing alert data: {column name: value}. See
            `self.fetch_alerts` for more information.

        Returns
        ----------
        out: GenericAlert
            Alert columns to be displayed on the TOM interface
        """
        # This URL points to the objectId page in the Fink Science Portal
        url = '{}/{}'.format(FINK_URL, alert['i:objectId'])

        return GenericAlert(
            timestamp=alert['i:jd'],
            id=alert['i:candid'],
            url=url,
            name=alert['i:objectId'],
            ra=alert['i:ra'],
            dec=alert['i:dec'],
            mag=alert['i:magpsf'],
            score=alert['d:rfscore']
        )
