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
Module for TestVirsh class.
"""
#
# IMPORTS
#
from tessia_baselib.common.ssh.shell import SshShell
from tessia_baselib.guests.linux.linux import GuestLinux
from tessia_baselib.hypervisors.kvm.virsh import Virsh
from unittest import mock

import unittest
#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
class TestVirsh(unittest.TestCase):
    """
    Class that provides the unit tests for the Virsh class.
    """
    def setUp(self):
        """
        Create mock objects and instantiate a Virsh object.
        """
        self._mock_guest_linux = mock.Mock(spec=GuestLinux)
        self._mock_ssh_shell = mock.Mock(spec=SshShell)
        self._virsh = Virsh(self._mock_guest_linux, self._mock_ssh_shell)
    # setUp()

    def test_init(self):
        """
        Test the proper initialization of the instance variables.
        """
        self.assertIs(self._virsh._cmd_channel, self._mock_ssh_shell)
        self.assertIs(self._virsh._host_cnn, self._mock_guest_linux)
    # test_init()

    @mock.patch("tessia_baselib.hypervisors.kvm.virsh.open", create=True)
    @mock.patch("tessia_baselib.hypervisors.kvm.virsh.mkstemp", spect_set=True)
    @mock.patch("tessia_baselib.hypervisors.kvm.virsh.os", spect_set=True)
    def test_define(self, mock_os, mock_mkstemp, mock_open):
        """
        Test the definition of a libvirt domain xml.
        """
        xml = "some xml"
        mock_file_descriptor = mock.Mock()
        path = "some path"
        source_url = "file://" + path
        mock_mkstemp.return_value = (mock_file_descriptor, path)
        domain_file = "some tmp file"
        self._mock_ssh_shell.run.side_effect = [
            (0, domain_file), (0, ""), (0, "")]

        self._virsh.define(xml)

        self.assertTrue(mock_mkstemp.called)
        self._mock_guest_linux.push_file.assert_called_with(source_url,
                                                            domain_file)
        mock_open.assert_called_with(mock_file_descriptor, mock.ANY)
        mock_open.return_value.write.assert_called_with(xml)
        mock_open.return_value.close.assert_called_with()
        mock_os.remove.assert_called_with(path)
        cmd = "virsh define {}".format(domain_file)
        self._mock_ssh_shell.run.assert_any_call(cmd)
    # test_define()

    @mock.patch("tessia_baselib.hypervisors.kvm.virsh.open", create=True)
    @mock.patch("tessia_baselib.hypervisors.kvm.virsh.mkstemp", spect_set=True)
    @mock.patch("tessia_baselib.hypervisors.kvm.virsh.os", spect_set=True)
    def test_define_mktemp_fails(self, mock_os, mock_mkstemp, mock_open):
        """
        Test the case the creation of a temporary file in the hypervisor
        fails.
        """
        mock_file_descriptor = mock.Mock()
        mock_mkstemp.return_value = (mock_file_descriptor, "")
        xml = "some xml"
        self._mock_ssh_shell.run.return_value = (1, "")

        self.assertRaisesRegex(RuntimeError, "Error while creating",
                               self._virsh.define, xml)
    # teste_define_mktemp_fails()

    @mock.patch("tessia_baselib.hypervisors.kvm.virsh.open", create=True)
    @mock.patch("tessia_baselib.hypervisors.kvm.virsh.mkstemp", spect_set=True)
    @mock.patch("tessia_baselib.hypervisors.kvm.virsh.os", spect_set=True)
    def test_define_define_fails(self, mock_os, mock_mkstemp, mock_open):
        """
        Test the case that the definition of the domain in the hypervisor
        fails.
        """
        mock_file_descriptor = mock.Mock()
        mock_mkstemp.return_value = (mock_file_descriptor, "")
        xml = "some xml"
        self._mock_ssh_shell.run.side_effect = [(0, ""), (1, "")]

        self.assertRaisesRegex(RuntimeError, "Error while defining domain",
                               self._virsh.define, xml)
    # teste_define_mktemp_fails()

    def test_destroy(self):
        """
        Test the virsh destroy command.
        """
        domain_name = "some domain"
        self._mock_ssh_shell.run.return_value = (0, "")
        cmd = "virsh destroy {}".format(domain_name)
        self._virsh.destroy(domain_name)
        self._mock_ssh_shell.run.assert_called_with(cmd)
    # test_destroy()

    def test_destroy_fails(self):
        """
        Test the case that the virsh destroy command fails.
        """
        domain_name = "some domain"
        self._mock_ssh_shell.run.return_value = (1, "")
        self.assertRaisesRegex(RuntimeError, "Error while destroying",
                               self._virsh.destroy, domain_name)
    # test_destroy_fails()

    def test_get_dominfo(self):
        """
        Test the virsh command dominfo.
        """
        domain_name = "some domain"
        cmd = "virsh dominfo {}".format(domain_name)
        dominfo_str = ("var1:     value1\n"
                       "var2:  value2\n"
                       "var3:    value3")
        self._mock_ssh_shell.run.return_value = (0, dominfo_str)

        dominfo = self._virsh.get_dominfo(domain_name)

        self._mock_ssh_shell.run.assert_called_with(cmd)
        self.assertEqual(dominfo["var2"], "value2")
    # test_get_dominfo()

    def test_get_dominfo_fails(self):
        """
        Test the case the virsh command dominfo fails.
        """
        domain_name = "some domain"
        self._mock_ssh_shell.run.return_value = (1, "")
        self.assertRaisesRegex(RuntimeError, "Error while getting dominfo",
                               self._virsh.get_dominfo, domain_name)
    # test_get_dominfo_fails()

    def test_is_defined_true(self):
        """
        Test if a domain is defined, expecting True.
        """
        domain_name = "some domain"
        dominfo_str = ("var1:     value1\n"
                       "var2:  value2\n"
                       "var3:    value3")

        self._mock_ssh_shell.run.return_value = (0, dominfo_str)

        self.assertTrue(self._virsh.is_defined(domain_name))
    # test_is_defined_true()

    def test_is_defined_false(self):
        """
        Test if a domain is defined, expecting False.
        """
        domain_name = "some domain"
        self._mock_ssh_shell.run.return_value = (1, "")
        self.assertFalse(self._virsh.is_defined(domain_name))
    # test_is_defined_false()

    def test_is_running_true(self):
        """
        Test the case is_running should return true.
        """
        domain_name = "some domain"
        dominfo_str = ("var1:     value1\n"
                       "State:  running\n"
                       "var3:    value3")
        self._mock_ssh_shell.run.return_value = (0, dominfo_str)
        self.assertTrue(self._virsh.is_running(domain_name))
    # test_is_running_true()

    def test_is_running_false_not_defined(self):
        """
        Test the case that a domain is not running because it is not defined.
        """
        domain_name = "some domain"
        self._mock_ssh_shell.run.return_value = (1, "")
        self.assertFalse(self._virsh.is_running(domain_name))
    # test_is_running_false_not_define()

    def test_is_running_false_halted(self):
        """
        Test the case that a domain is not running because it is halted.
        """
        domain_name = "some domain"
        dominfo_str = ("var1:     value1\n"
                       "State:  halt\n"
                       "var3:    value3")
        self._mock_ssh_shell.run.return_value = (0, dominfo_str)
        self.assertFalse(self._virsh.is_running(domain_name))
    # test_is_running_true()

    def test_reset(self):
        """
        Test the virsh reset command.
        """
        domain_name = "some domain"
        self._mock_ssh_shell.run.return_value = (0, "")
        cmd = "virsh reset {}".format(domain_name)
        self._virsh.reset(domain_name)
        self._mock_ssh_shell.run.assert_called_with(cmd)
    # test_reset()

    def test_reset_fails(self):
        """
        Test the case the virsh reset command fails.
        """
        domain_name = "some domain"
        self._mock_ssh_shell.run.return_value = (1, "")
        self.assertRaisesRegex(RuntimeError, "Error while reseting",
                               self._virsh.reset, domain_name)
    # test_reset_fails()

    def test_start(self):
        """
        Test the virsh start command.
        """
        domain_name = "some domain"
        self._mock_ssh_shell.run.return_value = (0, "")
        cmd = "virsh start {}".format(domain_name)
        self._virsh.start(domain_name)
        self._mock_ssh_shell.run.assert_called_with(cmd)
    # test_start()

    def test_start_fails(self):
        """
        Test the virsh start fails.
        """
        domain_name = "some domain"
        self._mock_ssh_shell.run.return_value = (1, "")
        self.assertRaisesRegex(RuntimeError, "Error while starting",
                               self._virsh.start, domain_name)
    # test_start_fails()

    def test_undefine(self):
        """
        Test the virsh undefine command.
        """
        domain_name = "some domain"
        self._mock_ssh_shell.run.return_value = (0, "")
        cmd = "virsh undefine {}".format(domain_name)
        self._virsh.undefine(domain_name)
        self._mock_ssh_shell.run.assert_called_with(cmd)
    # test_undefine()

    def test_undefine_fails(self):
        """
        Test the virsh undefine fails.
        """
        domain_name = "some domain"
        self._mock_ssh_shell.run.return_value = (1, "")
        self.assertRaisesRegex(RuntimeError, "Error while undefining",
                               self._virsh.undefine, domain_name)
    # test_undefine_fails()
# TestVirsh
