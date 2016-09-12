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
Module for the TestGuestKvm class.
"""
#
# IMPORTS
#
from tessia_baselib.common.ssh.shell import SshShell
from tessia_baselib.hypervisors.kvm.disk import DiskBase
from tessia_baselib.hypervisors.kvm.guest import GuestKvm
from tessia_baselib.hypervisors.kvm.guest import create_disk
from tessia_baselib.hypervisors.kvm.iface import Iface
from unittest import mock
from unittest.mock import sentinel

import unittest

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
class TestCreateDisk(unittest.TestCase):
    """
    Class that provides the unit tests for the create_disk factory method.
    """
    @mock.patch("tessia_baselib.hypervisors.kvm.guest.DISK_TYPEMAP", spec_set=True)
    def test_create_disk_scsi(self, mock_DISK_TYPEMAP):
        """
        Test the factory method create_disk for the regular usage.
        """
        parameters = {"disk_type": "SCSI"}
        mock_disk = mock.Mock(spec_set=DiskBase)

        mock_DISK_TYPEMAP.__getitem__.return_value = mock_disk
        mock_DISK_TYPEMAP.keys.return_value = ["SCSI", "DASD"]
        # Exercise the software
        disk = create_disk(parameters, sentinel.target_dev_mngr,
                           sentinel.cmd_channel)
        # Makes sure the disk was properly instantiaded
        mock_disk.assert_called_with(parameters,
                                     sentinel.target_dev_mngr,
                                     sentinel.cmd_channel)
        self.assertIs(disk, mock_disk.return_value)
    # test_create_disk_scsi()

    @mock.patch("tessia_baselib.hypervisors.kvm.guest.DISK_TYPEMAP", spec_set=True)
    def test_create_disk_unknow_fails(self, mock_DISK_TYPEMAP):
        """
        Test if the factory method create_disk properly fails when the
        disk_type is unknown.
        """
        parameters = {"disk_type": "OTHER_DISK_TYPE"}
        mock_DISK_TYPEMAP.keys.return_value = ["SCSI", "DASD"]
        self.assertRaisesRegex(RuntimeError, "Invalid or unknown",
                               create_disk, parameters,
                               sentinel.target_dev_mngr, sentinel.cmd_channel)
    # test_create_disk_unknown_fails()
# TestCreateDisk

class TestGuestKvm(unittest.TestCase):
    """
    Class that provides the unit tests for the GuestKvm class.
    """
    def setUp(self):
        """
        Initialize all the mocks used in all the unit tests.
        """
        # Create the mocks of the objects that are used as parameters
        # in the instantiation of the class.
        patcher = mock.patch(
            "tessia_baselib.hypervisors.kvm.guest.TargetDeviceManager")
        self._mock_tgt_dv_mngr = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch("tessia_baselib.hypervisors.kvm.guest.create_disk")
        self._mock_create_disk = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch("tessia_baselib.hypervisors.kvm.guest.Iface")
        self._mock_iface = patcher.start()
        self.addCleanup(patcher.stop)

        self._parameters = {
            "storage_volumes": [sentinel.volume1, sentinel.volume2],
            "ifaces": [sentinel.iface1, sentinel.iface2]
        }
        # Simulates the creation of two disks.
        self._disks = [mock.Mock(spec_set=DiskBase),
                       mock.Mock(spec_set=DiskBase)]
        self._mock_create_disk.side_effect = self._disks
        # Simulates the creation of two ifaces.
        self._ifaces = [mock.Mock(spec_set=Iface),
                        mock.Mock(spec_set=Iface)]
        self._mock_iface.side_effect = self._ifaces

        self._mock_ssh_shell = mock.Mock(spec_set=SshShell)
        # create the guest that is used in all tests
        self._guest = GuestKvm(sentinel.guest_name, sentinel.cpu,
                               sentinel.memory, self._parameters,
                               self._mock_ssh_shell)
    # setUp()

    def test_init(self):
        """
        Test the initial values of the instance.
        """
        self.assertIs(self._guest._guest_name, sentinel.guest_name)
        self.assertIs(self._guest._cpu, sentinel.cpu)
        self.assertIs(self._guest._memory, sentinel.memory)
        self.assertIs(self._guest._parameters, self._parameters)

        for i in range(len(self._disks)):
            self._mock_create_disk.assert_any_call(
                self._parameters.get("storage_volumes")[i],
                self._mock_tgt_dv_mngr.return_value,
                self._mock_ssh_shell)

        for i in range(len(self._ifaces)):
            self._mock_iface.assert_any_call(
                self._parameters.get("ifaces")[i],
                self._mock_tgt_dv_mngr.return_value)
    # test_init()

    def test_activate(self):
        """
        Test the activation procedure.
        """
        # Currently we only activate disks.
        self._guest.activate()
        for disk in self._disks:
            disk.activate.assert_called_with()
    # test_activate()

    @mock.patch("tessia_baselib.hypervisors.kvm.guest.open", create=True)
    def test_to_xml(self, mock_open):
        """
        Test that the guest object is properly converted to xml.
        """
        disk_xml = "disk_xml"
        for disk in self._disks:
            disk.to_xml.return_value = disk_xml

        iface_xml = "iface_xml"
        for iface in self._ifaces:
            iface.to_xml.return_value = iface_xml

        self._guest.to_xml()

        for disk in self._disks:
            disk.to_xml.assert_called_with()

        for iface in self._ifaces:
            iface.to_xml.assert_called_with()

        # since we have two disks and two interfaces, it is expected that
        # the content of the xml for disks and ifaces to be concatenated.
        mock_open.return_value.read.return_value.format.assert_called_with(
            name=sentinel.guest_name, memory=sentinel.memory,
            cpu=sentinel.cpu, disks=(disk_xml+disk_xml),
            ifaces=(iface_xml+iface_xml))
    # test_to_xml()
# TestGuestKvm
