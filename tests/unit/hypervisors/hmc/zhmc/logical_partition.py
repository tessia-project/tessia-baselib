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
from tessia_baselib.hypervisors.hmc.zhmc.exceptions import ZHmcRequestError

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
        # mock the time functions to skip waiting for sleeps
        self._patcher_time = mock.patch.object(
            logical_partition, 'time', autospec=True)
        self._mock_time = self._patcher_time.start()
        self.addCleanup(self._patcher_time.stop)
        def time_generator():
            """Generator for increasing time counter"""
            start = 1.1
            while True:
                start += 1.111
                yield start
        get_time = time_generator()
        self._mock_time.time.side_effect = lambda: next(get_time)

        self._mock_hmc = mock.MagicMock()
        self.lpar_name = 'dummy_name'
        self.lpar_uri = (
            '/api/logical-partitions/6f8dc862-c945-3abc-8773-f82846e7f476')
        self.lpar_status = 'dummy_status'
        self.lpar = logical_partition.LogicalPartition(
            self._mock_hmc,
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
        self.assertEqual(self._mock_hmc, self.lpar._hmc)
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
            self.lpar_uri + '/operations/send-os-cmd',
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
            self.lpar_uri + '/operations/activate',
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
            self.lpar_uri + '/operations/deactivate',
            body={
                'force': True
            }
        )

    # test_deactivate()

    def test_load_async(self):
        """
        Test if load() method work as expected in async mode (no timeout)

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """

        self.lpar.load('dummy_address')

        self._mock_hmc.session.json_request.assert_called_once_with(
            'POST',
            self.lpar_uri + '/operations/load',
            body={'load-address': 'dummy_address', 'force': True}
        )
    # test_load_async()

    def test_load_sync(self):
        """
        Test if load() method work as expected with normal timeout
        (synchronous).

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """

        self._mock_hmc.session.json_request.side_effect = [
            # response to POST /api/operations/load
            {"job-uri": "/api/jobs/cda161ce-d8d6-11e6-af32-5ef3fcb4c240"},
            # response to GET /api/jobs/cda161ce-d8d6-11e6-af32-5ef3fcb4c240
            {"status": "running"},
            # response to GET /api/jobs/cda161ce-d8d6-11e6-af32-5ef3fcb4c240
            {
                "status": "complete",
                "job-status-code": 204,
                "job-reason-code": 0
            },
        ]
        self.lpar.load('dummy_address', timeout=30)

        self._mock_hmc.session.json_request.assert_has_calls([
            mock.call(
                'POST',
                self.lpar_uri + '/operations/load',
                body={'load-address': 'dummy_address', 'force': True}
            ),
            mock.call(
                'GET',
                '/api/jobs/cda161ce-d8d6-11e6-af32-5ef3fcb4c240',
            ),
            mock.call(
                'GET',
                '/api/jobs/cda161ce-d8d6-11e6-af32-5ef3fcb4c240',
            ),
        ])

    # test_load_sync()

    def test_load_sync_timeout(self):
        """
        Test if load() method correctly raises exception when a timeout
        occurs.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """

        with self.assertRaisesRegex(
            ZHmcRequestError,
            'Timed out while waiting for load job completion'):
            self.lpar.load('dummy_address', timeout=30)

        session = self.lpar._hmc.session
        session.json_request.assert_any_call(
            'POST',
            self.lpar_uri + '/operations/load',
            body={
                'load-address': 'dummy_address',
                'force': True
            }
        )

    # test_load_sync_timeout()

    def test_scsi_load_async(self):
        """
        Test if scsi_load() method work as expected in async mode (no timeout)

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
            'dummy_lun',
        )

        session.json_request.assert_called_once_with(
            'POST',
            self.lpar_uri + '/operations/scsi-load',
            body={
                'load-address': 'dummy_address',
                'world-wide-port-name': 'dummy_wwpn',
                'logical-unit-number': 'dummy_lun',
                'force': True
            }
        )
    # test_scsi_load_async()

    def test_scsi_load_sync(self):
        """
        Test if scsi_load() method work as expected with normal timeout
        (synchronous).

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """

        self._mock_hmc.session.json_request.side_effect = [
            # response to POST /api/operations/load
            {"job-uri": "/api/jobs/cda161ce-d8d6-11e6-af32-5ef3fcb4c240"},
            # response to GET /api/jobs/cda161ce-d8d6-11e6-af32-5ef3fcb4c240
            {"status": "running"},
            # response to GET /api/jobs/cda161ce-d8d6-11e6-af32-5ef3fcb4c240
            {
                "status": "complete",
                "job-status-code": 204,
                "job-reason-code": 0
            },
        ]
        self.lpar.scsi_load(
            'dummy_address',
            'dummy_wwpn',
            'dummy_lun',
            timeout=30
        )

        # validate behavior
        self._mock_hmc.session.json_request.assert_has_calls([
            mock.call(
                'POST',
                self.lpar_uri + '/operations/scsi-load',
                body={
                    'load-address': 'dummy_address',
                    'world-wide-port-name': 'dummy_wwpn',
                    'logical-unit-number': 'dummy_lun',
                    'force': True
                }
            ),
            mock.call(
                'GET',
                '/api/jobs/cda161ce-d8d6-11e6-af32-5ef3fcb4c240',
            ),
            mock.call(
                'GET',
                '/api/jobs/cda161ce-d8d6-11e6-af32-5ef3fcb4c240',
            ),
        ])

    # test_scsi_load_sync()

    def test_scsi_load_sync_timeout(self):
        """
        Test if scsi_load() method correctly raises exception when a timeout
        occurs.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        with self.assertRaisesRegex(
            ZHmcRequestError,
            'Timed out while waiting for load job completion'):
            self.lpar.scsi_load(
                'dummy_address',
                'dummy_wwpn',
                'dummy_lun',
                timeout=30
            )

        session = self.lpar._hmc.session
        session.json_request.assert_any_call(
            'POST',
            self.lpar_uri + '/operations/scsi-load',
            body={
                'load-address': 'dummy_address',
                'world-wide-port-name': 'dummy_wwpn',
                'logical-unit-number': 'dummy_lun',
                'force': True
            }
        )
    # test_scsi_load_sync_timeout()

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
            "POST", self.lpar_uri + "/operations/stop", body=None
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
            self.lpar_uri + "/operations/reset-clear",
            body={
                "force": True
            }
        )
    # test_reset_clear()
