# Copyright 2017 IBM Corp.
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
Test module for the pool module.
"""

#
# IMPORTS
#
from tessia_baselib.guests.linux.linux import GuestLinux
from tessia_baselib.guests.linux.linux_session import GuestSessionLinux
from tessia_baselib.hypervisors.kvm.target_device_manager import \
    TargetDeviceManager
from tessia_baselib.hypervisors.kvm.storage import pool
from tessia_baselib.hypervisors.kvm.storage.disk_fcp import DiskFcp
from time import sleep
from unittest import mock
from unittest.mock import patch
from unittest import TestCase

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
class TestStoragePool(TestCase):
    """
    Test the StoragePool class
    """
    @staticmethod
    def _disk_id_gen():
        counter = 0
        while True:
            yield counter
            counter += 1
    # _disk_id_gen()

    def setUp(self):
        """
        Set up the mocks common to the testcases
        """
        id_generate = self._disk_id_gen()
        self._mock_disk = mock.Mock(spec_set=DiskFcp)
        self._mock_disk.side_effect = lambda a, b, c: mock.Mock(
            volume_id='disk{}'.format(next(id_generate))) # pylint: disable=unnecessary-lambda

        # DISK dictionary
        patcher = patch.dict(pool.DISK_TYPEMAP, {'FCP': self._mock_disk})
        self._mock_typemap = patcher.start()
        self.addCleanup(patcher.stop)

        # Target manager
        self._mock_tgt_mngr = mock.Mock(spec_set=TargetDeviceManager)
        # host connection
        self._mock_host_conn = mock.Mock(spec_set=GuestLinux)

        # mock sleep to avoid waiting
        patcher = patch.object(pool, 'sleep', autospec=True)
        patcher.start()
        self.addCleanup(patcher.stop)

        # create an instance for convenient usage
        self._volumes = [
            {
                'type': 'FCP',
                'specs': {
                    'multipath': False
                },
            },
            {
                'type': 'FCP',
                'specs': {
                    'multipath': True
                },
            },
        ]
        self._pool_obj = pool.StoragePool(
            self._volumes, self._mock_tgt_mngr, self._mock_host_conn)
    # setUp()

    def test_activate_success(self):
        """
        Exercise successful activation of disks
        """
        mock_session = mock.Mock(spec_set=GuestSessionLinux)
        self._mock_host_conn.open_session.return_value = mock_session
        mpath_cmds = [
            (0, ''), # rm and cp bak file
            (0, ''), # create conf file from template
            (0, ''), # 0 here means it's systemd (as opposed to sysv)
            (0, ''), # restart service
        ]
        mock_session.run.side_effect = mpath_cmds

        # mock each disk activate to successfully execute
        for disk in self._pool_obj._disks:
            disk.activate.side_effect = lambda: sleep(0.5)

        # perform action and validate behavior
        self._pool_obj.activate()
        self.assertEqual(mock_session.run.call_count, len(mpath_cmds))
        for disk in self._pool_obj._disks:
            disk.activate.assert_called_with()

        # pretend it's a sysv system
        mock_session.run.reset_mock()
        mpath_cmds[2] = (1, '')
        mock_session.run.side_effect = mpath_cmds

        # perform action and validate behavior
        self._pool_obj.activate()
        self.assertEqual(mock_session.run.call_count, len(mpath_cmds))
    # test_activate_success()

    def test_activate_fail_mpath(self):
        """
        Exercise failing to activate multipath service
        """
        mock_session = mock.Mock(spec_set=GuestSessionLinux)
        self._mock_host_conn.open_session.return_value = mock_session
        mock_session.run.side_effect = [
            (0, ''), # rm and cp bak file
            (1, ''), # failed to create conf file
        ]
        # perform action and validate behavior
        with self.assertRaisesRegex(
            RuntimeError, 'Failed to create /etc/multipath.conf'):
            self._pool_obj.activate()

        mock_session.run.side_effect = [
            (0, ''), # rm and cp bak file
            (0, ''), # failed to create conf file
            (0, ''), # 0 here means it's systemd (as opposed to sysv)
            (1, ''), # fail to restart service
        ]
        # perform action and validate behavior
        with self.assertRaisesRegex(
            RuntimeError, r'Failed to \(re\)start multipath daemon'):
            self._pool_obj.activate()

    # test_activate_fail_mpath()

    def test_activate_thread_fail(self):
        """
        Exercise the scenario where one of the disk activation threads fail
        """
        mock_session = mock.Mock(spec_set=GuestSessionLinux)
        self._mock_host_conn.open_session.return_value = mock_session
        mpath_cmds = [
            (0, ''), # rm and cp bak file
            (0, ''), # create conf file from template
            (0, ''), # 0 here means it's systemd (as opposed to sysv)
            (0, ''), # restart service
        ]
        mock_session.run.side_effect = mpath_cmds

        # mock one thread to succedeed and other to fail
        self._pool_obj._disks[0].activate.return_value = None
        self._pool_obj._disks[1].activate.side_effect = RuntimeError('Failed')
        failed_id = self._pool_obj._disks[1].volume_id

        # perform action and validate behavior
        with self.assertRaisesRegex(
            RuntimeError, 'Failed to activate disk {}'.format(failed_id)):
            self._pool_obj.activate()

    # test_activate_thread_fail()

    def test_init(self):
        """
        Exercise the constructor
        """
        # verify that multipath was set
        self.assertIs(self._pool_obj._mpath, True, 'Multipath was not set')

        # verify that correct disks were created
        self._mock_disk.assert_has_calls([
            mock.call(
                self._volumes[0], self._mock_tgt_mngr, self._mock_host_conn),
            mock.call(
                self._volumes[1], self._mock_tgt_mngr, self._mock_host_conn)
        ])
        self.assertEqual(len(self._pool_obj._disks), 2)

        # verify that multipath was NOT set
        volumes = [
            {
                'type': 'FCP',
            },
        ]
        pool_obj = pool.StoragePool(
            volumes, self._mock_tgt_mngr, self._mock_host_conn)
        self.assertIs(pool_obj._mpath, False, 'Multipath was set')

    # test_init()

    def test_init_invalid_type(self):
        """
        Exercise the constructor when an invalid disk type is specified
        """
        volumes = [
            {'type': 'INVALID'},
        ]
        with self.assertRaisesRegex(RuntimeError, 'Unknown disk type INVALID'):
            pool.StoragePool(
                volumes, self._mock_tgt_mngr, self._mock_host_conn)
    # test_init_invalid_type()

    def test_to_xml(self):
        """
        Exercise collecting the xml representation of each disk
        """
        expected_xml = ''
        for i in range(0, len(self._pool_obj._disks)):
            disk = self._pool_obj._disks[i]
            disk.to_xml.return_value = 'disk_xml{}'.format(i)
            expected_xml += disk.to_xml.return_value

        self.assertEqual(self._pool_obj.to_xml(), expected_xml)
# TestStoragePool
