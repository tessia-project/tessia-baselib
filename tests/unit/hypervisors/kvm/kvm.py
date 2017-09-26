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
from tessia_baselib.hypervisors.kvm import kvm
from unittest import mock

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
    },
    'mac_address': '02:57:52:01:ff:01',
    'type': 'MACVTAP'
}
DISK_FCP = {
    "type": "FCP",
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
    "type": "DASD",
    "volume_id": "3961",
}
START_PARAMETERS = {
    "storage_volumes" : [DISK_FCP, DISK_DASD],
    "ifaces" : [IFACE]
}
START_PARAMETERS_NETBOOT = {
    "storage_volumes" : [DISK_FCP, DISK_DASD],
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
        """
        Create the necessary mocks in order to isolate the object.
        """
        # guestlinux module
        patcher = mock.patch.object(kvm, "GuestLinux", spec_set=True)
        self._mock_guest_linux = patcher.start()
        self.addCleanup(patcher.stop)

        # virsh module
        patcher = mock.patch.object(kvm, 'Virsh', spec_set=True)
        self._mock_virsh = patcher.start()
        self.addCleanup(patcher.stop)

        # logger
        patcher = mock.patch.object(kvm, 'get_logger', spec_set=True)
        self._mock_logger = patcher.start().return_value
        self.addCleanup(patcher.stop)

        # create an instance for convenient use by testcases
        self.system_name = 'lpar054'
        self.host_name = 'lpar054.domain.com'
        self.user = 'root'
        self.passwd = 'somepasswd'
        self.parameters = {}
        self._hyp = kvm.HypervisorKvm(
            self.system_name, self.host_name, self.user, self.passwd,
            self.parameters)
    # setUp()

    def test_init(self):
        """
        Checks the correct initialization of the instance variables.

        """
        self.assertIs(self.system_name, self._hyp.name)
        self.assertIs(self.host_name, self._hyp.host_name)
        self.assertIs(self.user, self._hyp.user)
        self.assertIs(self.passwd, self._hyp.passwd)
        self.assertIs(self.parameters, self._hyp.parameters)
    # test_init()

    def test_login(self):
        """
        Test if the login procedure works as expected.
        """
        some_value = 44
        self._hyp.login(some_value)

        self._mock_guest_linux.assert_called_with(
            self.system_name, self.host_name, self.user, self.passwd,
            self.parameters)
        # assert connection was stablished
        self._mock_guest_linux.return_value.login.assert_called_with(
            some_value)
        self.assertIs(
            self._hyp._host_conn, self._mock_guest_linux.return_value)
        # assert virsh was created
        self.assertIs(
            self._hyp._virsh,
            self._mock_virsh.return_value)
        self._mock_logger.warning.assert_not_called()

        # exercise re-login
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

        self._mock_guest_linux.return_value.login.assert_any_call(60)
        self._mock_guest_linux.return_value.logoff.assert_called_with()
        self.assertIs(self._hyp._host_conn, None)

        self._mock_virsh.return_value.close.assert_called_with()
        self.assertIs(self._hyp._virsh, None)
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

    def test_stop(self):
        """
        Test the stop operation of the guest.
        """
        guest_name = "some guest"
        parameters_stop = {}
        self._mock_virsh.return_value.is_defined.return_value = True
        self._mock_virsh.return_value.is_running.return_value = True
        self._hyp.login()
        self._hyp.stop(guest_name, parameters_stop)
        self._mock_virsh.return_value.destroy.assert_called_with(guest_name)
    # test_stop()

    def test_stop_not_running(self):
        """
        Test the stop operation of the guest in the case it is not running.
        """
        guest_name = "some guest"
        parameters_stop = {}
        self._mock_virsh.return_value.is_defined.return_value = True
        self._mock_virsh.return_value.is_running.return_value = False
        self._hyp.login()
        self.assertRaisesRegex(RuntimeError, "is not running",
                               self._hyp.stop, guest_name, parameters_stop)
    # test_stop_not_running()

    def test_stop_not_defined(self):
        """
        Test the stop operation of the guest in the case it is not defined.
        """
        guest_name = "some guest"
        parameters_stop = {}
        self._mock_virsh.return_value.is_defined.return_value = False
        self._hyp.login()
        self.assertRaisesRegex(RuntimeError, "is not defined",
                               self._hyp.stop, guest_name, parameters_stop)
    # test_stop_not_defined()

    def test_reboot(self):
        """
        Test the reboot operation of the guest.
        """
        guest_name = "some guest"
        parameters_stop = {}
        self._mock_virsh.return_value.is_defined.return_value = True
        self._mock_virsh.return_value.is_running.return_value = True
        self._hyp.login()
        self._hyp.reboot(guest_name, parameters_stop)
        self._mock_virsh.return_value.destroy.assert_called_with(guest_name)
        self._mock_virsh.return_value.start.assert_called_with(guest_name)
    # test_reboot()

    def test_reboot_not_running(self):
        """
        Test the reboot operation of the guest in the case it is not running.
        """
        guest_name = "some guest"
        parameters_reboot = {}
        self._mock_virsh.return_value.is_defined.return_value = True
        self._mock_virsh.return_value.is_running.return_value = False
        self._hyp.login()
        self.assertRaisesRegex(RuntimeError, "is not running",
                               self._hyp.reboot, guest_name, parameters_reboot)
    # test_reboot_not_running()

    def test_reboot_not_defined(self):
        """
        Test the reboot operation of the guest in the case it is not defined.
        """
        guest_name = "some guest"
        parameters_reboot = {}
        self._mock_virsh.return_value.is_defined.return_value = False
        self._hyp.login()
        self.assertRaisesRegex(RuntimeError, "is not defined",
                               self._hyp.reboot, guest_name, parameters_reboot)
    # test_reboot_not_defined()

    @mock.patch("tessia_baselib.hypervisors.kvm.kvm.GuestKvm", spec_set=True)
    def test_start(self, mock_guest):
        """
        Test the start operation.
        """
        self._mock_virsh.return_value.is_running.return_value = True
        self._mock_virsh.return_value.is_defined.return_value = True
        guest_name = "some guest"
        cpu = 10
        memory = 4096

        self._hyp.login()
        self._hyp.start(guest_name, cpu, memory, START_PARAMETERS)

        mock_guest.assert_called_with(guest_name, cpu, memory,
                                      START_PARAMETERS,
                                      self._hyp._host_conn)
        mock_guest.return_value.activate.assert_called_with()
        self._mock_virsh.return_value.define.assert_called_with(
            mock_guest.return_value.to_xml.return_value)
        self._mock_virsh.return_value.start.assert_called_with(
            guest_name)
    # test_start()

    @mock.patch("tessia_baselib.hypervisors.kvm.kvm.GuestKvm", spec_set=True)
    def test_start_netboot(self, mock_guest):
        """
        Test the start operation in the case a network boot is performed.
        """
        self._mock_virsh.return_value.is_running.return_value = True
        self._mock_virsh.return_value.is_defined.return_value = True
        guest_name = "some guest"
        cpu = 10
        memory = 4096

        self._hyp.login()
        self._hyp.start(guest_name, cpu, memory, START_PARAMETERS_NETBOOT)

        mock_guest.assert_called_with(guest_name, cpu, memory,
                                      START_PARAMETERS_NETBOOT,
                                      self._hyp._host_conn)
        mock_guest.return_value.activate.assert_called_with()
        self._mock_virsh.return_value.define.assert_called_with(
            mock_guest.return_value.to_xml.return_value)
        self._mock_virsh.return_value.start.assert_called_with(
            guest_name)
        self._mock_virsh.return_value.define_netboot.assert_called_with(
            mock_guest.return_value.to_xml.return_value,
            START_PARAMETERS_NETBOOT.get("parameters").get("boot_options"))
    # test_start()

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

    @mock.patch("tessia_baselib.hypervisors.kvm.kvm.GuestKvm", spec_set=True)
    def test_start_clean_up_not_necessary(self, mock_guest):
        """
        Test the start in the case the clean up is not performed.
        """
        self._mock_virsh.return_value.is_running.return_value = False
        self._mock_virsh.return_value.is_defined.return_value = False
        guest_name = "some guest"
        cpu = 10
        memory = 4096

        self._hyp.login()
        self._hyp.start(guest_name, cpu, memory, START_PARAMETERS)

        mock_guest.assert_called_with(guest_name, cpu, memory,
                                      START_PARAMETERS,
                                      self._hyp._host_conn)
        mock_guest.return_value.activate.assert_called_with()
        self._mock_virsh.return_value.define.assert_called_with(
            mock_guest.return_value.to_xml.return_value)
        self._mock_virsh.return_value.start.assert_called_with(
            guest_name)
    # test_start_clean_up_not_necessary()

    @mock.patch("tessia_baselib.hypervisors.kvm.kvm.GuestKvm", spec_set=True)
    def test_start_param_none(self, mock_guest):
        """
        Confirm that the constructor accepts also None as value for the
        'parameter' attribute and works correctly.
        """
        self._mock_virsh.return_value.is_running.return_value = True
        self._mock_virsh.return_value.is_defined.return_value = True
        guest_name = "some guest"
        cpu = 10
        memory = 4096

        hyp_obj = kvm.HypervisorKvm(
            self.system_name, self.host_name, self.user, self.passwd, None)
        hyp_obj.login()
        hyp_obj.start(guest_name, cpu, memory, START_PARAMETERS)

        mock_guest.assert_called_with(
            guest_name, cpu, memory, START_PARAMETERS, hyp_obj._host_conn)
        mock_guest.return_value.activate.assert_called_with()
        self._mock_virsh.return_value.define.assert_called_with(
            mock_guest.return_value.to_xml.return_value)
        self._mock_virsh.return_value.start.assert_called_with(
            guest_name)
    # test_start_param_none()

# TestHypervisorKvm
