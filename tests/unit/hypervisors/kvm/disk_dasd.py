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
Test module for disk_dasd module.
"""

#
# IMPORTS
#
from tessia_baselib.common.ssh.shell import SshShell
from tessia_baselib.hypervisors.kvm.disk import DiskBase
from tessia_baselib.hypervisors.kvm.disk_dasd import DiskDasd
from tessia_baselib.hypervisors.kvm.target_device_manager \
    import TargetDeviceManager
from unittest import mock
from unittest import TestCase

#
# CONSTANTS AND DEFINITIONS
#
PARAMS_DASD = {
    "disk_type": "DASD",
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
        self._mock_tgt_dv_mngr = mock.Mock(spec=TargetDeviceManager)
        self._mock_ssh_shell = mock.Mock(spec=SshShell)
    # setUp()

    def _create_disk(self, parameters):
        """
        Auxiliary method to create a disk unsing the mock objects
        to initialize it.
        """
        return DiskDasd(parameters, self._mock_tgt_dv_mngr,
                        self._mock_ssh_shell)
    # _create_disk()

    def test_init(self):
        """
        Test the initialization of the instance variables.
        """
        disk = self._create_disk(PARAMS_DASD)
        self.assertEqual(disk._devicenr,
                         PARAMS_DASD.get("volume_id"))
    # test_init()

    @mock.patch("tessia_baselib.hypervisors.kvm.disk_dasd.DiskBase",
                autospec=True)
    @mock.patch("tessia_baselib.hypervisors.kvm.disk_dasd.timer",
                autospec=True)
    @mock.patch.object(DiskBase, "_enable_device")
    def test_activate(self, mock_enable_device, mock_timer, *args, **kwargs):
        """
        Test the activation of the disk when it is not active.
        """
        disk = self._create_disk(PARAMS_DASD)
        self._mock_ssh_shell.run.return_value = (1, "")

        disk.activate()

        check_cmd = "readlink -e '{}{}'".format(
            DASD_DEVPATH, PARAMS_DASD.get("volume_id"))

        mock_enable_device.assert_called_with(PARAMS_DASD.get("volume_id"))

        self._mock_ssh_shell.run.assert_called_with(check_cmd)

        mock_timer.assert_called_with(
            self._mock_ssh_shell, check_cmd, mock.ANY, mock.ANY)
        self.assertEqual(disk._source_dev, DASD_DEVPATH + disk._devicenr)
    # test_activate()

    @mock.patch("tessia_baselib.hypervisors.kvm.disk_dasd.DiskBase",
                autospec=True)
    @mock.patch.object(DiskBase, "_enable_device")
    @mock.patch("tessia_baselib.hypervisors.kvm.disk_dasd.timer",
                autospec=True)
    def test_already_activated(self, mock_timer, *args, **kwargs):
        """
        Test the case that the disk is already activated.
        """
        disk = self._create_disk(PARAMS_DASD)
        self._mock_ssh_shell.run.return_value = (0, "")
        disk.activate()

        check_cmd = "readlink -e '{}{}'".format(
            DASD_DEVPATH, PARAMS_DASD.get("volume_id"))

        self._mock_ssh_shell.run.assert_called_with(check_cmd)
        self.assertFalse(mock_timer.called)
    # test_already_activated()
# TestDiskDasd
