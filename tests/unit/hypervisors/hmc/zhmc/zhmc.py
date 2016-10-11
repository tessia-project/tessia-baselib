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
Unit test for the zhmc module
"""

#
# IMPORTS
#
from tessia_baselib.hypervisors.hmc.zhmc.zhmc import ZHmc
from tessia_baselib.hypervisors.hmc.zhmc.cpc import CPC
from tessia_baselib.hypervisors.hmc.zhmc.hmc_api_session import HmcApiSession
from tessia_baselib.hypervisors.hmc.zhmc.exceptions import ZHmcError
from unittest import TestCase
from unittest.mock import patch

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
class TestZHmc(TestCase):
    """
    Unit test for the ZHmc class
    """
    def setUp(self):
        """
        Setup a ZHmc object.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        # mock the libs required at the HmcApiSession class
        requests_patcher = patch(
            'tessia_baselib.hypervisors.hmc.zhmc.zhmc.HmcApiSession',
            spec_set=True
        )

        self._mock_requests = requests_patcher.start()
        self.addCleanup(requests_patcher.stop)

        host_name = 'dummy_host'
        user = 'dummy_user'
        passwd = 'dummy_passwd'
        port = 9999
        timeout = 60

        self.zhmc = ZHmc(
            host_name,
            user,
            passwd,
            port,
            timeout
        )

    # setUp()

    def test_attributes(self):
        """
        Validate if attributes were correctly assigned to object

        Raises:
            AssertionError: if validation fails
        """
        self.assertEqual(None, self.zhmc.cpcs)
        self.assertIsInstance(self.zhmc.session, HmcApiSession)
    # test_attributes()

    def test_get_cpc(self):
        """
        Test if get_cpc() method work as expected.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """

        fake_response = {
            'cpcs':
            [
                {
                    'name': 'dummy_cpc',
                    'object-uri': 'dummy.com',
                    'status': 'dummy_status'
                }
            ]
        }

        session = self.zhmc.session
        session.json_request.return_value = fake_response

        cpc = self.zhmc.get_cpc('dummy_cpc')
        self.assertIsInstance(cpc, CPC)
        self.assertEqual(cpc.name, 'dummy_cpc')
        self.assertEqual(cpc.uri, 'dummy.com')
        self.assertEqual(cpc.status, 'dummy_status')

        # check if error is raised when no cpc was found
        self.zhmc.cpcs = [{'name': 'different_name'}]
        with self.assertRaises(ZHmcError):
            self.zhmc.get_cpc('dummy_cpc')
    # test_get_cpc()
# TestZHmc
