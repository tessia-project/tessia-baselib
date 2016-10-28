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

#pylint:skip-file
"""
Module for TestDisk class.
"""

#
# IMPORTS
#
from tessia_baselib.common.ssh.shell import SshShell
from tessia_baselib.hypervisors.kvm.disk import DiskBase
from tessia_baselib.hypervisors.kvm.target_device_manager \
    import TargetDeviceManager

from unittest import mock

import unittest

#
# CONSTANTS AND DEFINITIONS
#
PARAMS_WITH_SYS_ATTRS = {
    "system_attributes": {
        "libvirt": "somexml"
    }
}

PARAMS_WITHOUT_SYS_ATTRS = {
}
#
# CODE
#


class TestDisk(unittest.TestCase):
    """
    Class that provides unit tests for the DiskBase class.
    """
    def setUp(self):
        """
        Create mocks that are used in all test cases.
        """
        self._mock_tgt_dv_mngr = mock.Mock(spec=TargetDeviceManager)
        self._mock_ssh_shell = mock.Mock(spec=SshShell)
    # setUp()

    def _create_disk(self, parameters):
        """
        Auxiliary method to create a disk.
        """
        return DiskBase(parameters, self._mock_tgt_dv_mngr,
                        self._mock_ssh_shell)

    def test_init_with_system_attrs(self):
        """
        Test the case that the disk is initiated with parameters
        containing a system_attributes properties.
        """
        disk = self._create_disk(PARAMS_WITH_SYS_ATTRS)

        self.assertIs(disk._parameters, PARAMS_WITH_SYS_ATTRS)
        self.assertIs(disk._source_dev, None)
        system_attributes = PARAMS_WITH_SYS_ATTRS.get("system_attributes")
        self.assertIs(disk._libvirt_xml, system_attributes.get("libvirt"))
        self._mock_tgt_dv_mngr.update_dev_blacklist.assert_called_once_with(
            system_attributes.get("libvirt"))
        self._mock_tgt_dv_mngr.update_devno_blacklist.assert_called_once_with(
            system_attributes.get("libvirt"))
        self.assertIs(disk._target_dev,
                      self._mock_tgt_dv_mngr.update_dev_blacklist.return_value)
        self.assertIs(
            disk._target_devno,
            self._mock_tgt_dv_mngr.update_devno_blacklist.return_value
        )
    # test_init_with_system_attrs()

    def test_init_without_system_attrs(self):
        """
        Test the case that the disk is initiated with parameters
        not containing a system_attributes properties.
        """
        disk = self._create_disk(PARAMS_WITHOUT_SYS_ATTRS)

        self.assertIs(disk._parameters, PARAMS_WITHOUT_SYS_ATTRS)
        self.assertIs(disk._source_dev, None)
        self._mock_tgt_dv_mngr.get_valid_dev.assert_called_once_with()
        self._mock_tgt_dv_mngr.get_valid_devno.assert_called_once_with()
        self.assertIs(disk._target_dev,
                      self._mock_tgt_dv_mngr.get_valid_dev.return_value)
        self.assertIs(disk._target_devno,
                      self._mock_tgt_dv_mngr.get_valid_devno.return_value)
    # test_init_without_system_attrs()

    def test_activate_not_implemented(self):
        """
        Test that the activate method is not implemented
        """
        disk = self._create_disk({})

        self.assertRaises(NotImplementedError, disk.activate)
    # test_activate_not_implemented()

    def test_disk_not_activate(self):
        """
        Test the case that the one tries to use to_xml method without
        activating the disk.
        """
        disk = self._create_disk({})
        self.assertRaisesRegex(RuntimeError, "The disk is not",
                               disk.to_xml)
    # test_disk_not_activate()

    def test_to_xml_with_libvirt_xml(self):
        """
        Test the case that a libvirt xml is provided to the disk.
        """
        disk = self._create_disk(PARAMS_WITH_SYS_ATTRS)

        source_dev = "/dev/dasda1"
        disk._source_dev = source_dev
        system_attrs = PARAMS_WITH_SYS_ATTRS.get("system_attributes")
        self.assertIs(system_attrs.get("libvirt"), disk.to_xml())
    # test_to_xml_with_libvirt_xml()

    @mock.patch("tessia_baselib.hypervisors.kvm.disk.open", create=True)
    def test_to_xml_read_template(self, mock_open):
        """
        Test the case that the libvirt xml is not provided and must
        be generated.
        """
        disk = self._create_disk({})
        source_dev = "/dev/dasda1"
        disk._source_dev = source_dev
        template_file = mock_open.return_value.read.return_value

        self.assertIs(
            disk.to_xml(),
            mock_open.return_value.read.return_value.format.return_value)

        template_file.format.assert_called_with(
            dev=source_dev,
            target_dev=self._mock_tgt_dv_mngr.get_valid_dev.return_value,
            devno=self._mock_tgt_dv_mngr.get_valid_devno.return_value,
            boot_tag="")
    # test_to_xml_reading_template()

    @mock.patch("tessia_baselib.hypervisors.kvm.disk.open", create=True)
    def test_to_xml_read_template_with_boot_tag(self, mock_open):
        """
        Test the case that the libvirt xml is not provided and must
        be generated. Also, the disk is a boot_device
        """
        disk = self._create_disk({"boot_device": True})
        source_dev = "/dev/dasda1"
        disk._source_dev = source_dev
        template_file = mock_open.return_value.read.return_value

        self.assertIs(
            disk.to_xml(),
            mock_open.return_value.read.return_value.format.return_value)

        template_file.format.assert_called_with(
            dev=source_dev,
            target_dev=self._mock_tgt_dv_mngr.get_valid_dev.return_value,
            devno=self._mock_tgt_dv_mngr.get_valid_devno.return_value,
            boot_tag='<boot order="1"/>')
    # test_to_xml_read_template_with_boot_tag()

    def test_enable_device(self):
        """
        Test the protected method that enable the device.
        """
        disk = self._create_disk({})
        devicenr = "some device number"

        self._mock_ssh_shell.run.side_effect = [(0, ""), (0, "")]
        disk._enable_device(devicenr)
        cmd1 = "echo free {} > /proc/cio_ignore".format(devicenr)
        cmd2 = 'chccwdev -e {}'.format(devicenr)
        calls = [mock.call(cmd1), mock.call(cmd2)]

        self.assertEqual(self._mock_ssh_shell.run.mock_calls, calls)
    # test_enable_device()

    def test_enable_device_fails(self):
        """
        Test the protected method that enable the device in the case
        it fails to enable.
        """
        disk = self._create_disk({})
        devicenr = "some device number"

        self._mock_ssh_shell.run.side_effect = [(0, ""), (1, "")]
        self.assertRaisesRegex(RuntimeError, "Failed to activate",
                               disk._enable_device, devicenr)
    # test_enable_device_fails()
# TestBaseDisk
