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

FINK_URL = "http://134.158.75.151:24000"
COLUMNS = 'i:candid,d:rfscore,i:ra,i:dec,i:jd,i:magpsf,i:objectId,d:cdsxmatch'

class FinkQueryForm(GenericQueryForm):
    """ Class to organise the Query Form for Fink.

    It currently contains forms for
        * ObjectId search

    """
    objectId = forms.CharField(required=False, label='ZTF Object ID')

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
