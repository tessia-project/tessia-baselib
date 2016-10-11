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
from tessia_baselib.hypervisors.hmc.zhmc.exceptions import ZHmcError
import itertools

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
        session = self.lpar._hmc.session
        session.json_request.side_effect = itertools.cycle([
            {'job-uri':'some_uri'},
            {'status': 'complete'},
            {'status': 'not-operating'}
        ])

        # test with force flag and image_profile name set
        job = self.lpar.activate(image_profile='dummy_profile', force=True)
        self.assertEqual(job['status-end'], 'not-operating')

        # test with no flag set
        job = self.lpar.activate()
        self.assertEqual(job['status-end'], 'not-operating')

        # set timeout to 0 so we do not need to wait
        logical_partition.ISSUE_OPERATION_WAIT_TIMEOUT = 0
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
        session = self.lpar._hmc.session
        session.json_request.side_effect = itertools.cycle([
            {'job-uri':'some_uri'},
            {'status': 'complete'},
            {'status': 'not-activated'}
        ])

        # test with force flag set
        job = self.lpar.deactivate(force=True)
        self.assertEqual(job['status-end'], 'not-activated')

        # test with no flag set
        job = self.lpar.deactivate()
        self.assertEqual(job['status-end'], 'not-activated')
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
        session = self.lpar._hmc.session
        session.json_request.side_effect = itertools.cycle([
            {'job-uri':'some_uri'},
            {'status': 'complete'},
            {'status': 'operating'}
        ])

        # test with force flag set
        job = self.lpar.load('dummy_address', force=True)
        self.assertEqual(job['status-end'], 'operating')

        # test with no flag set
        job = self.lpar.load('dummy_address')
        self.assertEqual(job['status-end'], 'operating')
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
        session.json_request.side_effect = itertools.cycle([
            {'job-uri':'some_uri'},
            {'status': 'complete'},
            {'status': 'operating'}
        ])

        # test with force flag set
        job = self.lpar.scsi_load(
            'dummy_address',
            'dummy_wwpn',
            'dummy_lun',
            force=True
        )
        self.assertEqual(job['status-end'], 'operating')

        # test with no flag set
        job = self.lpar.scsi_load(
            'dummy_address',
            'dummy_wwpn',
            'dummy_lun'
        )
        self.assertEqual(job['status-end'], 'operating')
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
        session = self.lpar._hmc.session
        session.json_request.side_effect = itertools.cycle([
            {'job-uri':'some_uri'},
            {'status': 'complete'},
            {'status': 'not-operating'}
        ])

        job = self.lpar.stop()
        self.assertEqual(job['status-end'], 'not-operating')
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
        session = self.lpar._hmc.session
        session.json_request.side_effect = itertools.cycle([
            {'job-uri':'some_uri'},
            {'status': 'complete'},
            {'status': 'not-operating'}
        ])

        # test with force flag set
        job = self.lpar.reset_clear(force=True)
        self.assertEqual(job['status-end'], 'not-operating')
        # test with no force flag set
        job = self.lpar.reset_clear()
        self.assertEqual(job['status-end'], 'not-operating')
    # test_reset_clear()

    def test_operation_on_timeout(self):
        """
        Test if the operation fails because some sort of timeout.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        # test timeout when the operation timeouts
        session = self.lpar._hmc.session
        session.json_request.side_effect = itertools.cycle([
            {'job-uri':'some_uri', 'status': 'running'}
        ])

        logical_partition.DEFAULT_JSON_REQUEST_TIMEOUT = 3
        with self.assertRaises(ZHmcError):
            self.lpar.reset_clear()
    # test_operation_on_timeout
