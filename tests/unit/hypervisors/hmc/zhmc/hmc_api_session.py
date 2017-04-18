# Copyright 2016, 2017 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Unit test for the hmc_api_session module
"""

#
# IMPORTS
#
from tessia_baselib.hypervisors.hmc.zhmc.exceptions import ZHmcRequestError
from tessia_baselib.hypervisors.hmc.zhmc.hmc_api_session import HmcApiSession
from unittest import mock
from unittest import TestCase
from unittest.mock import patch

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

class TestHmcApiSession(TestCase):
    """
    Unit test for the HmcApiSession class
    """
    def setUp(self):
        """
        Setup a HMC Api Session object.

        Args:
            None

        Raises:
            AssertionError: if validation fails
        """
        # mock the libs required at the Services class
        requests_patcher = patch(
            'tessia_baselib.hypervisors.hmc.zhmc.hmc_api_session.REQUESTS'
        )

        self._mock_requests = requests_patcher.start()
        self.addCleanup(requests_patcher.stop)

        self.host = 'dummy.com'
        self.user = 'dummy_user'
        self.passwd = 'dummy_passwd'
        self.port = 5555
        self.timeout = 60

        self.session = HmcApiSession(
            self.host, self.user, self.passwd, self.timeout, self.port)
    # setUp()

    def test_attributes(self):
        """
        Validate if attributes were correctly assigned to object

        Raises:
            AssertionError: if validation fails
        """
        self.assertEqual(self.host, self.session.host_name)
        self.assertEqual(self.user, self.session._user)
        self.assertEqual(self.passwd, self.session._passwd)
        self.assertEqual(self.port, self.session.port)
        self.assertEqual(self.timeout, self.session.timeout)
        self.assertIs(None, self.session.session_id)

        # test when the port is set to None
        self.session = HmcApiSession(
            self.host, self.user, self.passwd, self.timeout, None)
        self.assertEqual(6794, self.session.port)
    # test_attributes()

    def test_open_session(self):
        """
        Test if open_session() method work as expected.

        Args:
            None

        Raises:
            AssertionError: if validation fails
        """
        # setup a fake response
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"api-session": 999}
        self._mock_requests["POST"].return_value = resp

        url = "https://{}:{}/api/session".format(self.host, self.port)
        body = {
            'userid': self.session._user,
            'password': self.session._passwd
        }

        # regular scenario
        self.session.open_session()
        self._mock_requests["POST"].assert_called_with(
            url,
            headers={},
            json=body,
            verify=False,
            timeout=60
        )

        self.assertEqual(999, self.session.session_id)

    # test_open_session()

    def test_close_session(self):
        """
        Test if close_session() method work as expected.

        Args:
            None

        Raises:
            AssertionError: if validation fails
        """
        # setup a fake response
        resp = mock.MagicMock()
        resp.status_code = 204
        self._mock_requests["DELETE"].return_value = resp
        # since we will close the session, set a valid id
        self.session.session_id = 999

        url = "https://{}:{}/api/session/this-session".format(
            self.host, self.port)
        headers = dict()
        headers["X-API-Session"] = self.session.session_id

        # regular scenario
        self.session.close_session()
        self._mock_requests["DELETE"].assert_called_with(
            url,
            headers=headers,
            json=None,
            verify=False,
            timeout=60
        )

        self.assertIs(None, self.session.session_id)
    # test_close_session()

    def test_json_request(self):
        """
        Test if json_request method work as expected.

        Args:
            None

        Raises:
            AssertionError: if validation fails
        """
        # setup a fake response
        resp = mock.MagicMock()
        resp.status_code = 200
        self._mock_requests["GET"].return_value = resp
        # since we are testing a regular request, set a valid id
        self.session.session_id = 999

        url = "https://{}:{}/api/session".format(self.host, self.port)
        headers = dict()
        headers["X-API-Session"] = self.session.session_id

        # test regular scenario
        self.session.json_request(
            'GET',
            '/api/session'
        )
        self._mock_requests["GET"].assert_called_with(
            url,
            headers=headers,
            json=None,
            verify=False,
            timeout=60
        )

        # test setting optional parameters
        self.session.json_request(
            'GET',
            '/api/session',
            body={"foo": 1},
            headers={"bar": 2}
        )

        headers["bar"] = 2
        self._mock_requests["GET"].assert_called_with(
            url,
            headers=headers,
            json={"foo": 1},
            verify=False,
            timeout=60
        )

        # test when the requests fails
        resp.status_code = 404
        resp.json.return_value = {
            "reason": "foo", "message": "bar", "stack":"bar"
        }
        with self.assertRaises(ZHmcRequestError):
            self.session.json_request(
                'GET',
                '/api/session'
            )

        # test if there is an error in the json conversion
        resp.status_code = 200
        resp.json.side_effect = ValueError
        with self.assertRaises(ZHmcRequestError):
            self.session.json_request(
                'GET',
                '/api/session'
            )
    # test_json_request()
# TestHmcApiSession
