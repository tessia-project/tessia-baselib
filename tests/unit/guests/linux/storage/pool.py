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
from tessia_baselib.common.ssh.client import SshClient
from tessia_baselib.common.ssh.shell import SshShell
from tessia_baselib.guests.linux.storage import pool
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
        """Generator helper"""
        counter = 0
        while True:
            yield counter
            counter += 1
    # _disk_id_gen()

    def setUp(self):
        """
        Set up the mocks common to the testcases
        """
        # mock the disk objects
        id_generate = self._disk_id_gen()
        patcher = patch.object(pool, 'DiskFcp', autospec=True)
        self._mock_disk = patcher.start()
        self.addCleanup(patcher.stop)
        def mock_init(*args, **kwargs):
            """Helper to mock constructor of a disk class"""
            # validate call to constructor by the pool object
            self.assertEqual(len(args), 2)
            disk_mock = mock.Mock(volume_id='disk{}'.format(next(id_generate)))
            def mock_activate():
                """Helper to simulate time spent in disk activation"""
                sleep(0.1)
                return '/dev/{}'.format(disk_mock.volume_id)
            disk_mock.activate.side_effect = mock_activate
            return disk_mock
        self._mock_disk.side_effect = mock_init
        patcher = patch.object(pool, 'DiskDasd', autospec=True)
        mock_dasd = patcher.start()
        mock_dasd.side_effect = mock_init
        self.addCleanup(patcher.stop)
        # mock the dict as it already had a reference to the real class
        patcher = patch.dict(
            pool.DISK_TYPEMAP, {'FCP': self._mock_disk, 'DASD': mock_dasd})
        patcher.start()
        self.addCleanup(patcher.stop)

        # host connection
        self._mock_host_conn = mock.Mock(spec_set=SshClient)

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
        self._pool_obj = pool.StoragePool(self._volumes, self._mock_host_conn)
    # setUp()

    def test_activate_success(self):
        """
        Exercise successful activation of disks
        """
        mock_shell = mock.Mock(spec_set=SshShell)
        self._mock_host_conn.open_shell.return_value = mock_shell
        mpath_cmds = [
            (0, ''), # rm and cp bak file
            (0, ''), # create conf file from template
            (0, ''), # 0 here means it's systemd (as opposed to sysv)
            (0, ''), # restart service
        ]
        mock_shell.run.side_effect = mpath_cmds

        # perform action and validate behavior
        resp = self._pool_obj.activate()
        self.assertEqual(mock_shell.run.call_count, len(mpath_cmds))
        for disk in self._pool_obj._disks:
            self.assertEqual(
                resp[disk.volume_id], '/dev/{}'.format(disk.volume_id))
            disk.activate.assert_called_with()

        # pretend it's a sysv system
        mock_shell.run.reset_mock()
        mpath_cmds[2] = (1, '')
        mock_shell.run.side_effect = mpath_cmds

        # perform action and validate behavior
        self._pool_obj.activate()
        self.assertEqual(mock_shell.run.call_count, len(mpath_cmds))
    # test_activate_success()

    def test_activate_fail_mpath(self):
        """
        Exercise failing to activate multipath service
        """
        mock_shell = mock.Mock(spec_set=SshShell)
        self._mock_host_conn.open_shell.return_value = mock_shell
        mock_shell.run.side_effect = [
            (0, ''), # rm and cp bak file
            (1, ''), # failed to create conf file
        ]
        # perform action and validate behavior
        with self.assertRaisesRegex(
            RuntimeError, 'Failed to create /etc/multipath.conf'):
            self._pool_obj.activate()

        mock_shell.run.side_effect = [
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
        mock_shell = mock.Mock(spec_set=SshShell)
        self._mock_host_conn.open_shell.return_value = mock_shell
        mpath_cmds = [
            (0, ''), # rm and cp bak file
            (0, ''), # create conf file from template
            (0, ''), # 0 here means it's systemd (as opposed to sysv)
            (0, ''), # restart service
        ]
        mock_shell.run.side_effect = mpath_cmds

        # mock one thread to succedeed (already set in setUp) and other to fail
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
                self._volumes[0], self._mock_host_conn),
            mock.call(
                self._volumes[1], self._mock_host_conn)
        ])
        self.assertEqual(len(self._pool_obj._disks), 2)

        # verify that multipath was NOT set
        volumes = [
            {
                'type': 'FCP',
            },
        ]
        pool_obj = pool.StoragePool(volumes, self._mock_host_conn)
        self.assertIs(pool_obj._mpath, False, 'Multipath was set')

    # test_init()

    def test_init_invalid_type(self):
        """
        Exercise the constructor when an invalid disk type is specified
        """
        volumes = [{'type': 'INVALID'},]
        with self.assertRaisesRegex(RuntimeError, 'Unknown disk type INVALID'):
            pool.StoragePool(volumes, self._mock_host_conn)
    # test_init_invalid_type()
# TestStoragePool
