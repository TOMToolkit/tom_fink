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

from django import forms
import requests
import markdown as md

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
    Maximum window is 180 minutes (query can be very long!). This query will return all matching objects (not individual alerts).
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
        label='Class Search',
        help_text=md.markdown(
            help_classsearch
        ),
        widget=forms.TextInput(
            attrs={
                'placeholder': 'class, n_alert'
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
        if 'objectId' in parameters and len(parameters['objectId'].strip()) > 0:
            r = requests.post(
                FINK_URL + '/api/v1/objects',
                json={
                    'objectId': parameters['objectId'].strip(),
                    'columns': COLUMNS
                }
            )
        elif 'conesearch' in parameters and len(parameters['conesearch'].strip()) > 0:
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
        elif 'datesearch' in parameters and len(parameters['datesearch'].strip()) > 0:
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
        elif 'classsearch' in parameters and len(parameters['classsearch'].strip()) > 0:
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
