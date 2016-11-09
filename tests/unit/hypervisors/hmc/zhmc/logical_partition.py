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
Unit test for the logical_partition module
"""

#
# IMPORTS
#
from unittest import mock
from unittest import TestCase
from tessia_baselib.hypervisors.hmc.zhmc import logical_partition

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#


class TestLogicalPartition(TestCase):
    """
    Unit test for the LogicalPartition class
    """
    def setUp(self):
        """
        Setup a Activation lpar object.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        self.hmc_object = mock.Mock()
        self.lpar_name = 'dummy_name'
        self.lpar_uri = 'dummy.domain.com'
        self.lpar_status = 'dummy_status'
        self.lpar = logical_partition.LogicalPartition(
            self.hmc_object,
            self.lpar_name,
            self.lpar_uri,
            self.lpar_status
        )

    # setUp()

    def test_attributes(self):
        """
        Validate if attributes were correctly assigned to object

        Raises:
            AssertionError: if validation fails
        """
        self.assertEqual(self.hmc_object, self.lpar._hmc)
        self.assertEqual(self.lpar_name, self.lpar.name)
        self.assertEqual(self.lpar_uri, self.lpar.uri)
        self.assertEqual(self.lpar_status, self.lpar.status)
    # test_attributes()

    def test_get_properties(self):
        """
        Test if get_properties() method work as expected.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        # set fake response
        fake_response = {'status': 'dummy_status'}
        session = self.lpar._hmc.session
        session.json_request.return_value = fake_response

        prop = self.lpar.get_properties()

        # asserts
        self.assertEqual(prop, fake_response)
        session.json_request.assert_called_with(
            "GET",
            self.lpar.uri
        )
    # test_get_properties()

    def test_send_os_command(self):
        """
        Test if send_os_command() method work as expected.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """

        # test with image_profile name set
        self.lpar.send_os_command('some_command')
        session = self.lpar._hmc.session
        session.json_request.assert_called_with(
            'POST',
            'dummy.domain.com/operations/send-os-cmd',
            body={
                'operating-system-command-text': 'some_command'
            }
        )
    # test_send_os_command()

    def test_activate(self):
        """
        Test if activate() method work as expected.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """

        # test with image_profile name set
        self.lpar.activate(image_profile='dummy_profile')
        session = self.lpar._hmc.session
        session.json_request.assert_called_with(
            'POST',
            'dummy.domain.com/operations/activate',
            body={
                'activation-profile-name': 'dummy_profile',
                'force': True
            }
        )
    # test_activate()

    def test_deactivate(self):
        """
        Test if deactivate() method work as expected.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        self.lpar.deactivate()
        session = self.lpar._hmc.session
        session.json_request.assert_called_with(
            'POST',
            'dummy.domain.com/operations/deactivate',
            body={
                'force': True
            }
        )

    # test_deactivate()

    def test_load(self):
        """
        Test if load() method work as expected.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """

        self.lpar.load('dummy_address')

        session = self.lpar._hmc.session
        session.json_request.assert_called_with(
            'POST',
            'dummy.domain.com/operations/load',
            body={
                'load-address': 'dummy_address',
                'force': True
            }
        )

    # test_load()

    def test_scsi_load(self):
        """
        Test if scsi_load() method work as expected.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        session = self.lpar._hmc.session

        # test with force flag set
        self.lpar.scsi_load(
            'dummy_address',
            'dummy_wwpn',
            'dummy_lun'
        )

        session.json_request.assert_called_with(
            'POST',
            'dummy.domain.com/operations/scsi-load',
            body={
                'load-address': 'dummy_address',
                'world-wide-port-name': 'dummy_wwpn',
                'logical-unit-number': 'dummy_lun',
                'force': True
            }
        )
    # test_scsi_load()

    def test_stop(self):
        """
        Test if stop() method work as expected.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        self.lpar.stop()
        session = self.lpar._hmc.session
        session.json_request.assert_called_with(
            "POST", "dummy.domain.com/operations/stop", body=None
        )
    # test_stop()

    def test_reset_clear(self):
        """
        Test if reset_clear method work as expected.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        self.lpar.reset_clear()
        session = self.lpar._hmc.session
        session.json_request.assert_called_with(
            "POST",
            "dummy.domain.com/operations/reset-clear",
            body={
                "force": True
            }
        )
    # test_reset_clear()
