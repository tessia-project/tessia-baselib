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
Module for TestVirsh class.
"""

#
# IMPORTS
#
from tessia.baselib.guests.linux.linux import GuestLinux
from tessia.baselib.guests.linux.linux_session import GuestSessionLinux
from tessia.baselib.hypervisors.kvm import virsh
from unittest import mock
from unittest.mock import sentinel

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
        patcher = mock.patch(
            "tessia.baselib.hypervisors.kvm.virsh.ElementTree", autospec=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch("tessia.baselib.hypervisors.kvm.virsh.open")
        self._mock_open = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch(
            "tessia.baselib.hypervisors.kvm.virsh.mkstemp", autospec=True)
        self._mock_mkstemp = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch(
            "tessia.baselib.hypervisors.kvm.virsh.os.remove", autospec=True)
        self._mock_remove = patcher.start()
        self.addCleanup(patcher.stop)

        self._mock_guest_linux = mock.Mock(spec_set=GuestLinux)
        self._mock_session = mock.Mock(spec_set=GuestSessionLinux)
        self._mock_guest_linux.open_session.return_value = self._mock_session
        self._virsh = virsh.Virsh(self._mock_guest_linux)
    # setUp()

    def test_init(self):
        """
        Test the proper initialization of the instance variables.
        """
        self.assertIs(self._virsh._host_cnn, self._mock_guest_linux)
        self.assertIs(
            self._virsh._cmd_channel, self._mock_session)
    # test_init()

    def test_define(self):
        """
        Test the definition of a libvirt domain xml.
        """
        xml = "some xml"
        mock_file_descriptor = mock.Mock()
        path = "some path"
        source_url = "file://" + path
        self._mock_mkstemp.return_value = (mock_file_descriptor, path)
        mock_tmpdir = '/random_dir'
        domain_file = '{}/{}'.format(mock_tmpdir, virsh.DOMAIN_FILENAME)
        self._mock_session.run.side_effect = [
            (0, mock_tmpdir), # mktemp -d
            (0, ""), # chmod 755 {temp_dir}
            (0, ""), # virsh define {domain_file}
            (0, ""), # rm -f {domain_file}
            (0, "") # rm -rf {tmp_dir}
        ]

        self._virsh.define(xml)

        self.assertTrue(self._mock_mkstemp.called)
        self._mock_guest_linux.push_file.assert_called_with(
            source_url, domain_file)
        self._mock_open.assert_called_with(mock_file_descriptor, mock.ANY)
        self._mock_open.return_value.__enter__.return_value.write.\
            assert_called_with(xml)
        self._mock_remove.assert_called_with(path)
        cmd = "virsh define {}".format(domain_file)
        self._mock_session.run.assert_any_call(cmd)

        # validate correct closing the module
        tmp_dir = self._virsh._tmp_dir
        self._virsh.close()

        self._mock_session.run.assert_called_with(
            'rm -rf {}'.format(tmp_dir))
        self._mock_session.close.assert_called_with()
        self.assertIs(self._virsh._cmd_channel, None)

        self._mock_guest_linux.logoff.assert_not_called()
        self.assertIs(self._virsh._host_cnn, None)

    # test_define()

    def test_define_rm_tmpfile_fails(self):
        """
        Test the definition of a libvirt domain xml.
        """
        xml = "some xml"
        mock_file_descriptor = mock.Mock()
        path = "some path"
        source_url = "file://" + path
        self._mock_mkstemp.return_value = (mock_file_descriptor, path)
        mock_tmpdir = '/random_dir'
        domain_file = '{}/{}'.format(mock_tmpdir, virsh.DOMAIN_FILENAME)
        self._mock_session.run.side_effect = [
            (0, mock_tmpdir), (0, ""), (0, ""), (1, "")]

        self._virsh.define(xml)

        self.assertTrue(self._mock_mkstemp.called)
        self._mock_guest_linux.push_file.assert_called_with(source_url,
                                                            domain_file)
        self._mock_open.assert_called_with(mock_file_descriptor, mock.ANY)
        self._mock_open.return_value.__enter__.return_value.write.\
            assert_called_with(xml)
        self._mock_remove.assert_called_with(path)
        cmd = "virsh define {}".format(domain_file)
        self._mock_session.run.assert_any_call(cmd)
    # test_define_rm_tmpfile_fails()

    def test_define_netboot(self):
        """
        Test the definition of a domain xml used for network boot.
        """
        domain_xml = "some xml"
        boot_params = {
            "kernel_uri": sentinel.kernel_url,
            "initrd_uri": sentinel.initrd_url,
            "cmdline": sentinel.cmdline
        }
        mock_tmpdir = '/random_dir'
        mock_kernel = '{}/{}'.format(mock_tmpdir, virsh.KERNEL_FILENAME)
        mock_initrd = '{}/{}'.format(mock_tmpdir, virsh.INITRD_FILENAME)

        mock_file_descriptor = mock.Mock()
        path = "some path"
        self._mock_mkstemp.return_value = (mock_file_descriptor, path)
        domain_file = "some tmp file"

        self._mock_session.run.side_effect = [
            (0, mock_tmpdir),
            (0, domain_file), (0, ""), (0, "")]

        self._virsh.define_netboot(domain_xml, boot_params)

        self._mock_guest_linux.push_file.assert_any_call(
            boot_params.get("kernel_uri"), mock_kernel)
        self._mock_guest_linux.push_file.assert_any_call(
            boot_params.get("initrd_uri"), mock_initrd)
    # test_define_netboot()

    def test_define_netboot_tmp_files_exists(self):
        """
        Test the case that temporary files exist.
        """
        domain_xml = "some xml"
        boot_params = {
            "kernel_uri": sentinel.kernel_url,
            "initrd_uri": sentinel.initrd_url,
            "cmdline": sentinel.cmdline
        }
        mock_tmpdir = '/random_dir'
        mock_kernel = '{}/{}'.format(mock_tmpdir, virsh.KERNEL_FILENAME)
        mock_initrd = '{}/{}'.format(mock_tmpdir, virsh.INITRD_FILENAME)

        mock_file_descriptor = mock.Mock()
        path = "some path"
        self._mock_mkstemp.return_value = (mock_file_descriptor, path)

        self._mock_session.run.side_effect = [
            (0, mock_tmpdir), (0, ""), (0, ""), (0, "")]

        self._virsh.define_netboot(domain_xml, boot_params)

        self._mock_guest_linux.push_file.assert_any_call(
            boot_params.get("kernel_uri"), mock_kernel)
        self._mock_guest_linux.push_file.assert_any_call(
            boot_params.get("initrd_uri"), mock_initrd)
    # test_define_netboot_tmp_file_exists()

    def test_define_netboot_tmp_dir_fails(self):
        """
        Test the case that the creation of temporary dir fails.
        """
        boot_params = {
            "kernel_uri": sentinel.kernel_url,
            "initrd_uri": sentinel.initrd_url,
            "cmdline": sentinel.cmdline
        }
        domain_xml = "some xml"
        self._mock_session.run.return_value = (1, "")

        self.assertRaisesRegex(
            RuntimeError,
            "Error while creating temporary directory in the host:",
            self._virsh.define_netboot,
            domain_xml,
            boot_params)
    # test_define_netboot_tmp_dir_fails()

    def test_clean_tmp_dir(self):
        """
        Test the deletion of temporary directory.
        """
        self._mock_session.run.return_value = (1, mock.Mock())
        self._virsh.clean_tmp_dir()

        self._virsh._tmp_dir = sentinel.tmp_dir
        self._virsh.clean_tmp_dir()
        self._mock_session.run.assert_any_call(
            "rm -rf {}".format(sentinel.tmp_dir))

        self._mock_session.run.return_value = (0, mock.Mock())
        self._virsh.clean_tmp_dir()

    # test_clean_tmp_netboot_files()

    def test_define_mktemp_fails(self):
        """
        Test the case where the creation of a temporary dir in the hypervisor
        fails.
        """
        mock_file_descriptor = mock.Mock()
        self._mock_mkstemp.return_value = (mock_file_descriptor, "")
        xml = "some xml"
        self._mock_session.run.return_value = (1, "")

        self.assertRaisesRegex(RuntimeError, "Error while creating",
                               self._virsh.define, xml)
    # teste_define_mktemp_fails()

    def test_define_chmod_fails(self):
        """
        Test the case where setting permissions for the temporary dir in the
        hypervisor fails.
        """
        mock_file_descriptor = mock.Mock()
        self._mock_mkstemp.return_value = (mock_file_descriptor, "")
        xml = "some xml"
        self._mock_session.run.side_effect = [
            (0, ""), # mktemp -d
            (1, ""), # chmod 755 {temp_dir}
            (0, ""), # rm -rf {temp_dir}
        ]

        self.assertRaisesRegex(RuntimeError, "Failed to set permissions",
                               self._virsh.define, xml)
    # teste_define_mktemp_fails()

    def test_define_define_fails(self):
        """
        Test the case that the definition of the domain in the hypervisor
        fails.
        """
        mock_file_descriptor = mock.Mock()
        self._mock_mkstemp.return_value = (mock_file_descriptor, "")
        xml = "some xml"
        self._mock_session.run.side_effect = [
            (0, ""), # mktemp -d
            (0, ""), # chmod 755 {temp_dir}
            (1, ""), # virsh define
            (0, ""), # rm -rf {temp_dir}
        ]

        self.assertRaisesRegex(RuntimeError, "Error while defining domain",
                               self._virsh.define, xml)
    # teste_define_mktemp_fails()

    def test_destroy(self):
        """
        Test the virsh destroy command.
        """
        domain_name = "some domain"
        self._mock_session.run.return_value = (0, "")
        cmd = "virsh destroy {}".format(domain_name)
        self._virsh.destroy(domain_name)
        self._mock_session.run.assert_called_with(cmd)
    # test_destroy()

    def test_destroy_fails(self):
        """
        Test the case that the virsh destroy command fails.
        """
        domain_name = "some domain"
        self._mock_session.run.return_value = (1, "")
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
        self._mock_session.run.return_value = (0, dominfo_str)

        dominfo = self._virsh.get_dominfo(domain_name)

        self._mock_session.run.assert_called_with(cmd)
        self.assertEqual(dominfo["var2"], "value2")
    # test_get_dominfo()

    def test_get_dominfo_fails(self):
        """
        Test the case the virsh command dominfo fails.
        """
        domain_name = "some domain"
        self._mock_session.run.return_value = (1, "")
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

        self._mock_session.run.return_value = (0, dominfo_str)

        self.assertTrue(self._virsh.is_defined(domain_name))
    # test_is_defined_true()

    def test_is_defined_false(self):
        """
        Test if a domain is defined, expecting False.
        """
        domain_name = "some domain"
        self._mock_session.run.return_value = (1, "")
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
        self._mock_session.run.return_value = (0, dominfo_str)
        self.assertTrue(self._virsh.is_running(domain_name))
    # test_is_running_true()

    def test_is_running_false_not_defined(self):
        """
        Test the case that a domain is not running because it is not defined.
        """
        domain_name = "some domain"
        self._mock_session.run.return_value = (1, "")
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
        self._mock_session.run.return_value = (0, dominfo_str)
        self.assertFalse(self._virsh.is_running(domain_name))
    # test_is_running_true()

    def test_reset(self):
        """
        Test the virsh reset command.
        """
        domain_name = "some domain"
        self._mock_session.run.return_value = (0, "")
        cmd = "virsh reset {}".format(domain_name)
        self._virsh.reset(domain_name)
        self._mock_session.run.assert_called_with(cmd)
    # test_reset()

    def test_reset_fails(self):
        """
        Test the case the virsh reset command fails.
        """
        domain_name = "some domain"
        self._mock_session.run.return_value = (1, "")
        self.assertRaisesRegex(RuntimeError, "Error while reseting",
                               self._virsh.reset, domain_name)
    # test_reset_fails()

    def test_shutdown(self):
        """
        Test the virsh shutdown operation.
        """
        domain_name = "some domain"
        self._mock_session.run.return_value = (0, "")
        cmd_info = f"virsh dominfo {domain_name}"
        cmd_shutdown = f"virsh shutdown {domain_name}"
        self._virsh.shutdown(domain_name, timeout=2)
        self._mock_session.run.assert_has_calls([
            mock.call(cmd_shutdown), mock.call(cmd_info)
        ])
    # test_shutdown()

    def test_shutdown_timeout(self):
        """
        Test the virsh shutdown operation with a timeout.
        """
        domain_name = "some domain"
        self._mock_session.run.side_effect = [
            (0, ""),    # shutdown
            (0, "State:  running\n"), # dominfo
            (0, "")     # destroy
        ]
        cmd_info = f"virsh dominfo {domain_name}"
        cmd_shutdown = f"virsh shutdown {domain_name}"
        cmd_destroy = f"virsh destroy {domain_name}"
        self._virsh.shutdown(domain_name, timeout=-1)
        self._mock_session.run.assert_has_calls([
            mock.call(cmd_shutdown), mock.call(cmd_info),
            mock.call(cmd_destroy)
        ])
    # test_shutdown_timeout()

    def test_start(self):
        """
        Test the virsh start command.
        """
        domain_name = "some domain"
        self._mock_session.run.return_value = (0, "")
        cmd = "virsh start {}".format(domain_name)
        self._virsh.start(domain_name)
        self._mock_session.run.assert_called_with(cmd)
    # test_start()

    def test_start_fails(self):
        """
        Test the virsh start fails.
        """
        domain_name = "some domain"
        self._mock_session.run.return_value = (1, "")
        self.assertRaisesRegex(RuntimeError, "Error while starting",
                               self._virsh.start, domain_name)
    # test_start_fails()

    def test_undefine(self):
        """
        Test the virsh undefine command.
        """
        domain_name = "some domain"
        self._mock_session.run.return_value = (0, "")
        cmd = "virsh undefine {}".format(domain_name)
        self._virsh.undefine(domain_name)
        self._mock_session.run.assert_called_with(cmd)
    # test_undefine()

    def test_undefine_fails(self):
        """
        Test the virsh undefine fails.
        """
        domain_name = "some domain"
        self._mock_session.run.return_value = (1, "")
        self.assertRaisesRegex(RuntimeError, "Error while undefining",
                               self._virsh.undefine, domain_name)
    # test_undefine_fails()
# TestVirsh
