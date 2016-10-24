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
Test module for kvm module
"""

#
# IMPORTS
#
from tessia_baselib.hypervisors.kvm.kvm import HypervisorKvm
from unittest import mock
from unittest.mock import sentinel

import unittest

#
# CONSTANTS AND DEFINITIONS
#
IFACE = {
    "attributes":
    {
        "libvirt": '''<interface type="direct">
        <mac address="02:57:52:01:ff:01"/>
        <source dev="eth0" mode="bridge"/>
        <model type="virtio"/>
        <address type="ccw" cssid="0xfe" ssid="0x0" devno="0xf500"/>
    </interface>'''
    }
}
DISK_SCSI = {
    "disk_type": "SCSI",
    "volume_id": "1024400000000000",
    "boot_device": True,
    "specs": {
        "multipath": True,
        "adapters": [{
            "devno": "0.0.1800",
            "wwpns": ['300607630503c1ae']
        }]
    }
}
DISK_DASD = {
    "disk_type": "DASD",
    "volume_id": "3961",
}
START_PARAMETERS = {
    "storage_volumes" : [DISK_SCSI, DISK_DASD],
    "ifaces" : [IFACE]
}
START_PARAMETERS_NETBOOT = {
    "storage_volumes" : [DISK_SCSI, DISK_DASD],
    "ifaces" : [IFACE],
    "parameters": {
        "boot_method": "network",
        "boot_options": {
            "kernel_uri": "http://kernel",
            "initrd_uri": "http://initrd",
            "cmdline": "some cmdline"
        }
    }
}
#
# CODE
#

class TestHypervisorKvm(unittest.TestCase):
    """
    Class that provides unit tests for the HypervisorKvm class.
    """
    def setUp(self):
        patcher = mock.patch("tessia_baselib.hypervisors.kvm.kvm.GuestLinux",
                             spec_set=True)
        self._mock_guest_linux = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch("tessia_baselib.hypervisors.kvm.kvm.get_logger",
                             spec_set=True)
        self._mock_logger = patcher.start().return_value
        self.addCleanup(patcher.stop)
        self._hyp = HypervisorKvm(sentinel.system_name,
                                  sentinel.host_name,
                                  sentinel.user,
                                  sentinel.passwd,
                                  sentinel.parameters)
    # setUp()

    def test_init(self):
        """
        Checks the correct initialization of the instance variables.

        """
        self.assertIs(sentinel.system_name, self._hyp.name)
        self.assertIs(sentinel.host_name, self._hyp.host_name)
        self.assertIs(sentinel.user, self._hyp.user)
        self.assertIs(sentinel.passwd, self._hyp.passwd)
        self.assertIs(sentinel.parameters, self._hyp.parameters)

        self._mock_guest_linux.assert_called_with(sentinel.system_name,
                                                  sentinel.host_name,
                                                  sentinel.user,
                                                  sentinel.passwd,
                                                  sentinel.parameters)
    # test_init()

    def test_login(self):
        """
        Test if the login procedure works as expected.
        """
        some_value = 44
        self._hyp.login(some_value)

        self._mock_guest_linux.return_value.login.assert_called_with(
            some_value)

        self.assertIs(
            self._hyp._host_session,
            self._mock_guest_linux.return_value.open_session.return_value)
        self._mock_logger.warning.assert_not_called()

        # in order to achieve 100% coverage
        self._hyp.login()
        self._mock_logger.warning.assert_called_with(
            "Login called with connection already active: dropping"
            " previous connection object")
    # test_login()

    def test_logoff(self):
        """
        Test if the logoff procedure works as expected.
        """
        self._hyp.login()
        self._hyp.logoff()

        host_session = (
            self._mock_guest_linux.return_value.open_session.return_value)
        host_session.close.assert_called_with()

        self._mock_guest_linux.return_value.logoff.assert_called_with()
        self.assertIs(self._hyp._host_session, None)

    # test_logoff()

    def test_operations_fails_without_login(self):
        """
        Test that the operations fails if performed without doing login first.
        """
        guest_name = "some guest"
        cpu = 10
        memory = 4096
        self.assertRaisesRegex(RuntimeError, "You must login first",
                               self._hyp.start, guest_name, cpu, memory,
                               START_PARAMETERS)
        self.assertRaisesRegex(RuntimeError, "You must login first",
                               self._hyp.stop, guest_name, {})
        self.assertRaisesRegex(RuntimeError, "You must login first",
                               self._hyp.reboot, guest_name, {})
        self.assertRaisesRegex(RuntimeError, "You must login first",
                               self._hyp.logoff)
    # test_logoff_fails()

    @mock.patch("tessia_baselib.hypervisors.kvm.kvm.Virsh", spec_set=True)
    def test_stop(self, mock_virsh):
        """
        Test the stop operation of the guest.
        """
        guest_name = "some guest"
        parameters_stop = {}
        mock_virsh.return_value.is_defined.return_value = True
        mock_virsh.return_value.is_running.return_value = True
        self._hyp.login()
        self._hyp.stop(guest_name, parameters_stop)
        mock_virsh.return_value.destroy.assert_called_with(guest_name)
    # test_stop()

    @mock.patch("tessia_baselib.hypervisors.kvm.kvm.Virsh", spec_set=True)
    def test_stop_not_running(self, mock_virsh):
        """
        Test the stop operation of the guest in the case it is not running.
        """
        guest_name = "some guest"
        parameters_stop = {}
        mock_virsh.return_value.is_defined.return_value = True
        mock_virsh.return_value.is_running.return_value = False
        self._hyp.login()
        self.assertRaisesRegex(RuntimeError, "is not running",
                               self._hyp.stop, guest_name, parameters_stop)
    # test_stop_not_running()

    @mock.patch("tessia_baselib.hypervisors.kvm.kvm.Virsh", spec_set=True)
    def test_stop_not_defined(self, mock_virsh):
        """
        Test the stop operation of the guest in the case it is not defined.
        """
        guest_name = "some guest"
        parameters_stop = {}
        mock_virsh.return_value.is_defined.return_value = False
        self._hyp.login()
        self.assertRaisesRegex(RuntimeError, "is not defined",
                               self._hyp.stop, guest_name, parameters_stop)
    # test_stop_not_defined()

    @mock.patch("tessia_baselib.hypervisors.kvm.kvm.Virsh", spec_set=True)
    def test_reboot(self, mock_virsh):
        """
        Test the reboot operation of the guest.
        """
        guest_name = "some guest"
        parameters_stop = {}
        mock_virsh.return_value.is_defined.return_value = True
        mock_virsh.return_value.is_running.return_value = True
        self._hyp.login()
        self._hyp.reboot(guest_name, parameters_stop)
        mock_virsh.return_value.reset.assert_called_with(guest_name)
    # test_reboot()

    @mock.patch("tessia_baselib.hypervisors.kvm.kvm.Virsh", spec_set=True)
    def test_reboot_not_running(self, mock_virsh):
        """
        Test the reboot operation of the guest in the case it is not running.
        """
        guest_name = "some guest"
        parameters_reboot = {}
        mock_virsh.return_value.is_defined.return_value = True
        mock_virsh.return_value.is_running.return_value = False
        self._hyp.login()
        self.assertRaisesRegex(RuntimeError, "is not running",
                               self._hyp.reboot, guest_name, parameters_reboot)
    # test_reboot_not_running()

    @mock.patch("tessia_baselib.hypervisors.kvm.kvm.Virsh", spec_set=True)
    def test_reboot_not_defined(self, mock_virsh):
        """
        Test the reboot operation of the guest in the case it is not defined.
        """
        guest_name = "some guest"
        parameters_reboot = {}
        mock_virsh.return_value.is_defined.return_value = False
        self._hyp.login()
        self.assertRaisesRegex(RuntimeError, "is not defined",
                               self._hyp.reboot, guest_name, parameters_reboot)
    # test_reboot_not_defined()

    @mock.patch("tessia_baselib.hypervisors.kvm.kvm.Virsh", spec_set=True)
    @mock.patch("tessia_baselib.hypervisors.kvm.kvm.GuestKvm", spec_set=True)
    def test_start(self, mock_guest, mock_virsh):
        """
        Test the start operation.
        """
        mock_virsh.return_value.is_running.return_value = True
        mock_virsh.return_value.is_defined.return_value = True
        guest_name = "some guest"
        cpu = 10
        memory = 4096

        self._hyp.login()
        self._hyp.start(guest_name, cpu, memory, START_PARAMETERS)

        mock_guest.assert_called_with(guest_name, cpu, memory,
                                      START_PARAMETERS,
                                      self._hyp._host_session)
        mock_guest.return_value.activate.assert_called_with()
        mock_virsh.return_value.define.assert_called_with(
            mock_guest.return_value.to_xml.return_value)
        mock_virsh.return_value.start.assert_called_with(
            guest_name)
    # test_start()

    @mock.patch("tessia_baselib.hypervisors.kvm.kvm.Virsh", spec_set=True)
    @mock.patch("tessia_baselib.hypervisors.kvm.kvm.GuestKvm", spec_set=True)
    def test_start_netboot(self, mock_guest, mock_virsh):
        """
        Test the start operation in the case a network boot is performed.
        """
        mock_virsh.return_value.is_running.return_value = True
        mock_virsh.return_value.is_defined.return_value = True
        guest_name = "some guest"
        cpu = 10
        memory = 4096

        self._hyp.login()
        self._hyp.start(guest_name, cpu, memory, START_PARAMETERS_NETBOOT)

        mock_guest.assert_called_with(guest_name, cpu, memory,
                                      START_PARAMETERS_NETBOOT,
                                      self._hyp._host_session)
        mock_guest.return_value.activate.assert_called_with()
        mock_virsh.return_value.define.assert_called_with(
            mock_guest.return_value.to_xml.return_value)
        mock_virsh.return_value.start.assert_called_with(
            guest_name)
        mock_virsh.return_value.define_netboot.assert_called_with(
            mock_guest.return_value.to_xml.return_value,
            START_PARAMETERS_NETBOOT.get("parameters").get("boot_options"))
    # test_start()

    @mock.patch("tessia_baselib.hypervisors.kvm.kvm.Virsh", spec_set=True)
    @mock.patch("tessia_baselib.hypervisors.kvm.kvm.GuestKvm", spec_set=True)
    def test_start_not_logged_in(self, *args, **kwargs):
        """
        Test the start operation when it is not logged in the hypervisor.
        """
        guest_name = "some guest"
        cpu = 10
        memory = 4096
        self.assertRaisesRegex(RuntimeError, "You must login first",
                               self._hyp.start, guest_name, cpu, memory,
                               START_PARAMETERS)
    # test_start_not_logged_in()

    @mock.patch("tessia_baselib.hypervisors.kvm.kvm.Virsh", spec_set=True)
    @mock.patch("tessia_baselib.hypervisors.kvm.kvm.GuestKvm", spec_set=True)
    def test_start_clean_up_not_necessary(self, mock_guest, mock_virsh):
        """
        Test the start in the case the clean up is not performed.
        """
        mock_virsh.return_value.is_running.return_value = False
        mock_virsh.return_value.is_defined.return_value = False
        guest_name = "some guest"
        cpu = 10
        memory = 4096

        self._hyp.login()
        self._hyp.start(guest_name, cpu, memory, START_PARAMETERS)

        mock_guest.assert_called_with(guest_name, cpu, memory,
                                      START_PARAMETERS,
                                      self._hyp._host_session)
        mock_guest.return_value.activate.assert_called_with()
        mock_virsh.return_value.define.assert_called_with(
            mock_guest.return_value.to_xml.return_value)
        mock_virsh.return_value.start.assert_called_with(
            guest_name)
    # test_start_clean_up_not_necessary()
# TestHypervisorKvm
