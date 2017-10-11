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
Test module for disk_dasd module.
"""

#
# IMPORTS
#
from tessia_baselib.common import utils
from tessia_baselib.common.ssh.client import SshClient
from tessia_baselib.common.ssh.shell import SshShell
from tessia_baselib.guests.linux.storage.disk_dasd import DiskDasd
from unittest import mock
from unittest import TestCase
from unittest.mock import patch

#
# CONSTANTS AND DEFINITIONS
#
PARAMS_DASD = {
    "type": "DASD",
    "volume_id": "3961",
}
# The DEVICE path for a dasd disk was copied here to detect future changes in
# the format (eg.: by an udev update)
DASD_DEVPATH = "/dev/disk/by-path/ccw-0.0."

#
# CODE
#

class TestDiskDasd(TestCase):
    """
    Class that provides unit tests for the DiskDasd class.
    """
    def setUp(self):
        """
        Create mocks that are used in all test cases to initialize
        the disk.
        """
        # mock sleep in timer
        patcher = patch.object(utils, 'sleep', autospec=True)
        patcher.start()
        self.addCleanup(patcher.stop)

        self._mock_host_conn = mock.Mock(spec_set=SshClient)
        self._mock_shell = mock.Mock(spec_set=SshShell)
        self._mock_host_conn.open_shell.return_value = self._mock_shell
    # setUp()

    def _create_disk(self, parameters):
        """
        Auxiliary method to create a disk unsing the mock objects
        to initialize it.
        """
        return DiskDasd(parameters, self._mock_host_conn)
    # _create_disk()

    def test_activate(self):
        """
        Test the activation of the disk when it is not active.
        """
        outputs = [
            (1, ""), # readlink -e
            (0, ""), # _enable_device echo free cio_ignore
            (0, ""), # _enable_device chccwdev -e
            (0, ""), # readlink -e
        ]
        self._mock_shell.run.side_effect = outputs

        disk = self._create_disk(PARAMS_DASD)
        self.assertEqual(disk.activate(), DASD_DEVPATH + disk._devicenr)
    # test_activate()

    def test_already_activated(self):
        """
        Test the case that the disk is already activated.
        """
        self._mock_shell.run.return_value = (0, "")

        disk = self._create_disk(PARAMS_DASD)
        self.assertEqual(disk.activate(), DASD_DEVPATH + disk._devicenr)
    # test_already_activated()
# TestDiskDasd
