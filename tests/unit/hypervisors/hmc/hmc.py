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
Testing class for the HMC hypervisor
"""

#
# IMPORTS
#
from tessia_baselib.hypervisors.hmc import hmc
from tessia_baselib.hypervisors.hmc.zhmc.exceptions import ZHmcError
from unittest import mock
from unittest import TestCase
from unittest.mock import patch

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
class TestHypervisorHmc(TestCase):
    """
    Unit test for the HypervisorHmc class
    """
    def setUp(self):
        """
        Setup a HypervisorHmc object and related mocks.
        """
        self.system_name = 'dummy_system'
        self.host_name = 'dummy.domain.com'
        self.user = 'root'
        self.passwd = 'somepwd'
        self.parameters = {}

        # mock the ZHmc class
        self._patcher_zhmc = patch.object(hmc, 'ZHmc')
        self._mock_zhmc = self._patcher_zhmc.start()

        # mock the logger returned by get_logger
        self._patcher_logger = patch.object(hmc, 'get_logger')
        self._mock_get_logger = self._patcher_logger.start()
        self._mock_logger = mock.Mock(
            spec=['info', 'warning', 'error', 'debug'])
        self._mock_get_logger.return_value = self._mock_logger

        # instantiate the object to be used in the testcases
        self.hmc_object = hmc.HypervisorHmc(
            self.system_name,
            self.host_name,
            self.user,
            self.passwd,
            self.parameters
        )
    # setUp()

    def tearDown(self):
        """
        Stop patching the mocks. Before each test setUp will be executed and
        the patch created again.
        """
        self._patcher_logger.stop()
        self._patcher_zhmc.stop()
    # tearDown()

    def test_attributes(self):
        """
        Validate if attributes were correctly assigned to object

        Raises:
            AssertionError: if validation fails
        """
        self.assertEqual('hmc', self.hmc_object.HYP_ID)
        self.assertEqual(self.system_name, self.hmc_object.name)
        self.assertEqual(self.host_name, self.hmc_object.host_name)
        self.assertEqual(self.user, self.hmc_object.user)
        self.assertEqual(self.passwd, self.hmc_object.passwd)
        self.assertEqual(self.parameters, self.hmc_object.parameters)
    # test_attributes()

    def test_login(self):
        """
        Check if the login() method works as expected

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        # regular scenario
        self.hmc_object.login()
        self.assertIs(self.hmc_object._session, self._mock_zhmc.return_value)

        # test login on already active connection
        self.hmc_object.login()
        self._mock_logger.warning.assert_called_with(
            "Login called with connection already active:"
            " dropping previous connection object"
        )
    # test_login()

    def test_logoff(self):
        """
        Check if the logoff() method works as expected

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        # check if exception is raised on logoff performed without previous
        # login
        with self.assertRaises(ZHmcError):
            self.hmc_object.logoff()

        # set the return value so the logoff can properly work
        session = self._mock_zhmc.return_value.session = mock.Mock()
        session.close_session.return_value = "foo"

        # regular scenario
        self.hmc_object.login()
        self.hmc_object.logoff()

        # check if session was really reset
        self.assertIs(self.hmc_object._session, None)
    # test_logoff()

    def test_start(self):
        """
        Check if the logoff() method works as expected

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        # setting up the mock objects
        mock_lpar = (
            # pylint: disable=no-member
            self._mock_zhmc.return_value.get_cpc.return_value.
            get_lpar.return_value
        )
        mock_image_profile = (
            # pylint: disable=no-member
            self._mock_zhmc.return_value.get_cpc.return_value.
            get_image_profile.return_value
        )
        mock_image_profile.get_properties.return_value = {
            'central-storage': 4096,
            'number-shared-general-purpose-processors': 5,
            'number-shared-ifl-processors': 1
        }

        # check if exception is raised on start performed without previous
        # login
        with self.assertRaises(ZHmcError):
            parameters = {
                'cpc_name': 'dummy',
                'boot_params': {
                    "boot_method": "dasd",
                    "devicenr": "9999"
                }
            }

            self.hmc_object.start('dummy', 'dummy', 'dummy', parameters)

        # regular scenario
        self.hmc_object.login()

        # perform the operation when the image profile needs to update cpu
        # and memory using a DASD disk
        lpar_name = 'dummy_lpar'
        cpu = 10
        memory = 1024
        parameters = {
            'cpc_name': 'my_cpc',
            'boot_params': {
                'boot_method': 'dasd',
                'devicenr': '9999'
            }
        }

        self.hmc_object.start(lpar_name, cpu, memory, parameters)
        mock_lpar.activate.assert_called_with(force=True)
        mock_lpar.load.assert_called_with('9999')

        # test in case of operation error
        mock_lpar.load.side_effect = ZHmcError('Error')
        with self.assertRaises(ZHmcError):
            self.hmc_object._logger = mock.create_autospec(
                self.hmc_object._logger
            )
            self.hmc_object.start(lpar_name, cpu, memory, parameters)
            self._mock_logger.debug.assert_called_with(
                "An error ocurred, should we roll back?"
            )

            # reset side effect
            mock_lpar.load.side_effect = mock.DEFAULT

        # perform the operation when the image profile do not need update
        # using a SCSI disk
        parameters = {
            'cpc_name': 'my_cpc',
            'boot_params': {
                'boot_method': 'scsi',
                'iface_devicenr':'1234',
                'wwpn': '4321',
                'lun': '1324'
            },
            'ifl_cpus': 1
        }

        cpu = 6
        memory = 4096
        mock_lpar.status = 'not-activated'
        self.hmc_object.start(lpar_name, cpu, memory, parameters)
        mock_lpar.activate.assert_called_with()
        mock_lpar.scsi_load.assert_called_with('1234', '4321', '1324')
    # test_start()

    def test_stop(self):
        """
        Check if the stop() method works as expected

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        mock_lpar = (
            # pylint: disable=no-member
            self._mock_zhmc.return_value.get_cpc.return_value.
            get_lpar.return_value
        )
        mock_lpar.status = 'operating'

        # check if exception is raised on stop performed without previous
        # login
        with self.assertRaises(ZHmcError):
            self.hmc_object.stop('dummy', {'cpc_name': 'my_cpc'})

        # regular scenario
        self.hmc_object.login()
        self.hmc_object.stop('my_lpar', {'cpc_name': 'my_cpc'})
        mock_lpar.stop.assert_called_with()
        mock_lpar.reset_clear.assert_called_with()

        # test operation on invalid lpar status
        mock_lpar.status = 'dummy_status'
        with self.assertRaises(ZHmcError):
            self.hmc_object.stop('my_lpar', {'cpc_name': 'my_cpc'})
    # test_stop()

    def test_reboot(self):
        """
        Check if the reboot() method works as expected

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        with self.assertRaises(NotImplementedError):
            self.hmc_object.reboot('dummy', {})
    # test_reboot()
# TestHypervisorHmc
