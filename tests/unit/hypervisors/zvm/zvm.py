# Copyright 2017, 2018 IBM Corp.
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
Test module for zvm hypervisor
"""

#
# IMPORTS
#
from tessia.baselib.hypervisors.zvm import zvm
from tessia.baselib.guests.cms import cms as cms_module
from tests.unit.guests.cms.cms import patch_s3270
from unittest import mock
from unittest import TestCase
from unittest.mock import patch

import os
import re
import yaml

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
class TestHypervisorZvm(TestCase):
    """
    Unit test for the HypervisorZvm class
    """
    def _patch_cms(self):
        """
        Mock the GuestCms object used by the Hypervisor object and return them

        Returns:
            tuple: patched HypervisorZvm object, mocked GuestCms class
        """
        patcher = patch.object(zvm, 'GuestCms', autospec=True)
        mock_cms_cls = patcher.start()
        self.addCleanup(patcher.stop)

        # create object for convenient access
        hyp = zvm.HypervisorZvm(
            self._name, self._hostname, self._user, self._passwd, None)

        return hyp, mock_cms_cls
    # _patch_cms()

    def _patch_s3270(self, mock_outputs):
        """
        Mock the underlying s3270 object to use mocked console outputs and
        return the resulting patched hypervisor object

        Args:
            mock_outputs (list): mocked console outputs

        Returns:
            tuple: patched HypervisorZvm object, mocked s3270 object
        """
        hyp = zvm.HypervisorZvm(
            self._name, self._hostname, self._user, self._passwd, None)

        # patch the s3270 object in order to use mocked console outputs
        cms_obj = hyp._cms
        mock_s3270 = patch_s3270(self, cms_obj, mock_outputs)

        # this patching is needed in order to assure the terminal object keeps
        # using our mocked s3270 even after a disconnect
        orig_logoff = cms_obj._terminal.logoff
        def mock_terminal_logoff(*args, **kwargs):
            """
            Call original logoff and re-set the mocked s3270 back.
            """
            orig_logoff(*args, **kwargs)
            cms_obj._terminal._s3270 = mock_s3270
        # mock_terminal_logoff()
        cms_obj._terminal.logoff = mock_terminal_logoff

        return hyp, mock_s3270
    # _patch_s3270()

    @classmethod
    def setUpClass(cls):
        """
        Store the console output data to be used in the tests.
        """
        data_file = '{}/zvm.yaml'.format(
            os.path.dirname(os.path.abspath(__file__)))
        with open(data_file, 'r', encoding='utf-8') as data_fd:
            cls._data = yaml.safe_load(data_fd.read())

        cls._user = 'USER'
        cls._name = 'hostname'
        cls._hostname = 'hostname.com'
        cls._passwd = 'password'
    # setUpClass()

    def test_login(self):
        """
        Exercise a normal login command
        """
        hyp, mock_cms_cls = self._patch_cms()
        hyp.login()
        mock_cms_cls.assert_called_once_with(
            self._user, self._hostname, self._user, self._passwd,
            {'here': True, 'noipl': True})
        mock_cms_cls.return_value.login.assert_called_once_with()
    # test_login()

    def test_logoff(self):
        """
        Exercise a normal logoff command
        """
        hyp, mock_cms_cls = self._patch_cms()
        hyp.login()
        hyp.logoff()
        mock_cms_cls.return_value.logoff.assert_called_once_with()
    # test_logoff()

    def test_reboot(self):
        """
        Verify that reboot is not currently implemented
        """
        hyp, _ = self._patch_cms()
        hyp.login()
        with self.assertRaises(NotImplementedError):
            hyp.reboot(self._user, None)
    # test_reboot()

    def test_start_cms(self):
        """
        Exercise an IPL of CMS (no boot disk specified)
        """
        mock_outputs = []
        # use the disk outputs as a base and strip the last steps where the
        # disk ipl is done
        for entry in self._data['start_dasd']:
            if ' I 1C5D' in entry:
                break
            mock_outputs.append(entry)
        # add the ipl cms step
        mock_outputs.extend(self._data['start_cms'])

        hyp, mock_s3270 = self._patch_s3270(mock_outputs)

        # perform start
        guest_cpu = 2
        guest_memory = 2048
        iface = {"type": "osa", "id": "f5f0,f5f1,f5f2"}
        disk_dasd = {"type": "dasd", "devno": "1c5d", "boot_device": True}
        guest_parameters = {
            "boot_method": "cms",
            "storage_volumes" : [disk_dasd],
            "ifaces" : [iface]
        }
        hyp.login()
        hyp.start(self._user, guest_cpu, guest_memory, guest_parameters)

        # validate commands executed
        call_list = [
            mock.call('l {} here noipl'.format(self._user)),
            mock.call(self._passwd, hide=True),
            mock.call('#cp term more 50 10'),
            mock.call(r'#cp i cms\naccess (noprof'),
            mock.call('#cp term more 50 10'),
            mock.call('#cp system clear'),
            mock.call('#cp logoff'),
            mock.call('l {} here noipl'.format(self._user)),
            # second login attempt due to a force/logoff pending in the
            # mocked output
            mock.call('l {} here noipl'.format(self._user)),
            mock.call(self._passwd, hide=True),
            mock.call('begin'),
            mock.call('#cp term more 50 10'),
            mock.call(r'#cp i cms\naccess (noprof'),
            mock.call('#cp term more 50 10'),
            mock.call('#cp detach cpu all'),
            mock.call('#cp define storage {}M'.format(guest_memory)),
            mock.call('q v cpus'),
            mock.call('define cpu 1'),
            mock.call('q v  1c5d'),
            mock.call('q v  f5f0'),
            mock.call('q v  f5f1'),
            mock.call('q v  f5f2'),
            mock.call(r'i cms\naccess (noprof'),
            mock.call('#cp term more 50 10'),
        ]
        self.assertListEqual(mock_s3270.string.mock_calls, call_list)
    # test_start_cms()

    def test_start_cms_fail(self):
        """
        Exercise an IPL of CMS which fails
        """
        mock_outputs = []
        for entry in self._data['start_dasd']:
            pattern = ' I 1C5D'
            if re.search(pattern, entry):
                new_entry = re.sub(
                    pattern, 'HCP052E Error in CP directory', entry)
                mock_outputs.append(new_entry)
                break
            mock_outputs.append(entry)
        hyp, _ = self._patch_s3270(mock_outputs)

        # perform start
        guest_cpu = 2
        guest_memory = 2048
        iface = {"type": "osa", "id": "f5f0,f5f1,f5f2"}
        disk_dasd = {"type": "dasd", "devno": "1c5d", "boot_device": True}
        guest_parameters = {
            "boot_method": "cms",
            "storage_volumes" : [disk_dasd],
            "ifaces" : [iface]
        }
        hyp.login()
        with self.assertRaisesRegex(RuntimeError, 'Failed to IPL CMS'):
            hyp.start(self._user, guest_cpu, guest_memory, guest_parameters)
    # test_start_cms_fail()

    def test_start_dasd(self):
        """
        Exercise an IPL of a DASD disk
        """
        hyp, mock_s3270 = self._patch_s3270(self._data['start_dasd'])

        # perform start
        guest_cpu = 2
        guest_memory = 2048
        iface = {"type": "osa", "id": "f5f0,f5f1,f5f2"}
        disk_dasd = {"type": "dasd", "devno": "1c5d", "boot_device": True}
        guest_parameters = {
            "boot_method": "disk",
            "storage_volumes" : [disk_dasd],
            "ifaces" : [iface]
        }
        hyp.login()
        hyp.start(self._user, guest_cpu, guest_memory, guest_parameters)

        # validate commands executed
        call_list = [
            mock.call('l {} here noipl'.format(self._user)),
            mock.call(self._passwd, hide=True),
            mock.call('#cp term more 50 10'),
            mock.call(r'#cp i cms\naccess (noprof'),
            mock.call('#cp term more 50 10'),
            mock.call('#cp system clear'),
            mock.call('#cp logoff'),
            mock.call('l {} here noipl'.format(self._user)),
            # second login attempt due to a force/logoff pending in the
            # mocked output
            mock.call('l {} here noipl'.format(self._user)),
            mock.call(self._passwd, hide=True),
            mock.call('begin'),
            mock.call('#cp term more 50 10'),
            mock.call(r'#cp i cms\naccess (noprof'),
            mock.call('#cp term more 50 10'),
            mock.call('#cp detach cpu all'),
            mock.call('#cp define storage {}M'.format(guest_memory)),
            mock.call('q v cpus'),
            mock.call('define cpu 1'),
            mock.call('q v  1c5d'),
            mock.call('q v  f5f0'),
            mock.call('q v  f5f1'),
            mock.call('q v  f5f2'),
            mock.call('i 1c5d'),
        ]
        self.assertListEqual(mock_s3270.string.mock_calls, call_list)
    # test_start_dasd()

    def test_start_dasd_fail(self):
        """
        Exercise an IPL of a DASD disk which fails to reach the login prompt
        """
        # remove the last output containing the login prompt
        hyp, _ = self._patch_s3270(self._data['start_dasd'][:-1])

        # perform start
        guest_cpu = 2
        guest_memory = 2048
        iface = {"type": "osa", "id": "f5f0,f5f1,f5f2"}
        disk_dasd = {"type": "dasd", "devno": "1c5d", "boot_device": True}
        guest_parameters = {
            "boot_method": "disk",
            "storage_volumes" : [disk_dasd],
            "ifaces" : [iface]
        }
        hyp.login()
        with self.assertRaisesRegex(RuntimeError, 'Failed to IPL disk'):
            hyp.start(self._user, guest_cpu, guest_memory, guest_parameters)
    # test_start_dasd_fail()

    def test_start_fcp(self):
        """
        Exercise an IPL of a FCP disk
        """
        hyp, mock_s3270 = self._patch_s3270(self._data['start_fcp'])

        # perform start
        guest_cpu = 2
        guest_memory = 2048
        iface = {"type": "osa", "id": "f5f0,f5f1,f5f2"}
        disk_scsi = {
            "type": "fcp",
            "adapters": [
                {"devno": "1740", "wwpns": ["100507630503c5ae"]},
                {"devno": "0.0.1780", "wwpns": ["100507630503c7ae"]},
            ],
            "lun": "1022400d00000000",
            "boot_device": True,
        }
        guest_parameters = {
            "boot_method": "disk",
            "storage_volumes" : [disk_scsi],
            "ifaces" : [iface]
        }
        hyp.login()
        hyp.start(self._user, guest_cpu, guest_memory, guest_parameters)

        # validate commands executed
        call_list = [
            mock.call('l {} here noipl'.format(self._user)),
            mock.call(self._passwd, hide=True),
            mock.call('#cp term more 50 10'),
            mock.call(r'#cp i cms\naccess (noprof'),
            mock.call('#cp term more 50 10'),
            mock.call('#cp system clear'),
            mock.call('#cp logoff'),
            mock.call('l {} here noipl'.format(self._user)),
            mock.call(self._passwd, hide=True),
            mock.call('begin'),
            mock.call('#cp term more 50 10'),
            mock.call(r'#cp i cms\naccess (noprof'),
            mock.call('#cp term more 50 10'),
            mock.call('#cp detach cpu all'),
            mock.call('#cp define storage {}M'.format(guest_memory)),
            mock.call('q v cpus'),
            mock.call('define cpu 1'),
            mock.call('q v  1740'),
            mock.call('att  1740 *'),
            mock.call('q v  1780'),
            mock.call('att  1780 *'),
            mock.call('q v  f5f0'),
            mock.call('q v  f5f1'),
            mock.call('q v  f5f2'),
            mock.call('set loaddev portname 10050763 0503c5ae lun 1022400d '
                      '00000000'),
            mock.call('q loaddev'),
            mock.call('i 1740')
        ]
        self.assertListEqual(mock_s3270.string.mock_calls, call_list)
    # test_start_fcp()

    def test_start_invalid(self):
        """
        Exercise invalid starts:
        - when boot method is disk but no boot device was defined.
        - when guest name is different than username provided for login
        - when boot method is network but no netboot parameters were defined.
        """
        hyp, _ = self._patch_cms()
        guest_cpu = 2
        guest_memory = 2048
        iface = {"type": "osa", "id": "f5f0,f5f1,f5f2"}
        disk_dasd = {"type": "dasd", "devno": "1c5d"}
        guest_params = {
            "boot_method": "disk",
            "storage_volumes" : [disk_dasd],
            "ifaces" : [iface],
        }
        hyp.login()
        error_msg = "Boot method 'disk' requires a boot device"
        with self.assertRaisesRegex(ValueError, error_msg):
            hyp.start(self._user, guest_cpu, guest_memory, guest_params)

        error_msg = 'guest name provided must be the same as the username'
        with self.assertRaisesRegex(ValueError, error_msg):
            hyp.start('DUMMY', guest_cpu, guest_memory, guest_params)

        guest_params['boot_method'] = 'network'
        error_msg = "Boot method 'network' requires netboot parameters"
        with self.assertRaisesRegex(ValueError, error_msg):
            hyp.start(self._user, guest_cpu, guest_memory, guest_params)
    # test_start_invalid()

    def test_start_netboot(self):
        """
        Exercise an IPL via network
        """
        mock_outputs = []
        # use the disk outputs as a base and strip the last steps where the
        # disk ipl is done
        for entry in self._data['start_dasd']:
            # strip the last steps where a disk ipl is done
            if ' I 1C5D' in entry:
                break
            mock_outputs.append(entry)
        # add the netboot steps
        mock_outputs.extend(self._data['start_netboot'])

        hyp, mock_s3270 = self._patch_s3270(mock_outputs)
        # mock transfer calls
        mock_s3270.transfer.side_effect = 3 * [
            r'U U U C(hostname.com) I 4 24 80 0 0 0x0 0.072\n'
            r'ok\n']

        # now we need to mock the requests library to prevent an actual
        # download to happen
        patcher = patch.object(cms_module.requests, 'get', autospec=True)
        mock_get = patcher.start()
        self.addCleanup(patcher.stop)
        mock_resp = mock_get.return_value
        mock_resp.raise_for_status.return_value = None
        mock_resp.iter_content.return_value = ['1', '2', '3']

        # mock temp file creation
        patcher = patch.object(cms_module, 'NamedTemporaryFile', autospec=True)
        mock_temp_cls = patcher.start()
        self.addCleanup(patcher.stop)
        mock_file = mock_temp_cls.return_value.__enter__.return_value
        mock_file.name = 'local_temp_file'

        # perform the netboot
        guest_cpu = 2
        guest_memory = 2048
        iface = {"type": "osa", "id": "f5f0,f5f1,f5f2"}
        disk_dasd = {"type": "dasd", "devno": "1c5d"}
        guest_params = {
            "boot_method": "network",
            "storage_volumes" : [disk_dasd],
            "ifaces" : [iface],
            "netboot": {
                "cmdline": "param1=value1 param2=value2",
                "kernel_uri": "http://_install-server.com/distro/kernel.img",
                "initrd_uri": "http://_install-server.com/distro/initrd.img",
            }
        }
        hyp.login()
        hyp.start(self._user, guest_cpu, guest_memory, guest_params)

        # validate commands executed
        call_list = [
            mock.call('l {} here noipl'.format(self._user)),
            mock.call(self._passwd, hide=True),
            mock.call('#cp term more 50 10'),
            mock.call(r'#cp i cms\naccess (noprof'),
            mock.call('#cp term more 50 10'),
            mock.call('#cp system clear'),
            mock.call('#cp logoff'),
            mock.call('l {} here noipl'.format(self._user)),
            # second login attempt due to a force/logoff pending in the
            # mocked output
            mock.call('l {} here noipl'.format(self._user)),
            mock.call(self._passwd, hide=True),
            mock.call('begin'),
            mock.call('#cp term more 50 10'),
            mock.call(r'#cp i cms\naccess (noprof'),
            mock.call('#cp term more 50 10'),
            mock.call('#cp detach cpu all'),
            mock.call('#cp define storage {}M'.format(guest_memory)),
            mock.call('q v cpus'),
            mock.call('define cpu 1'),
            mock.call('q v  1c5d'),
            mock.call('q v  f5f0'),
            mock.call('q v  f5f1'),
            mock.call('q v  f5f2'),
            mock.call(r'i cms\naccess (noprof'),
            mock.call('#cp term more 50 10'),
            mock.call('q v ffff'),
            mock.call('define vfb-512 as ffff blk 200000'),
            mock.call(r'format ffff t\n1\ntmpdsk'),
            mock.call('spool punch *'),
            mock.call('close reader'),
            mock.call('purge reader all'),
            mock.call('punch {} (noh'.format(
                zvm.HypervisorZvm.NETBOOT_KERNEL_FILE)),
            mock.call('punch {} (noh'.format(
                zvm.HypervisorZvm.NETBOOT_CMDLINE_FILE)),
            mock.call('punch {} (noh'.format(
                zvm.HypervisorZvm.NETBOOT_INITRD_FILE)),
            mock.call('change reader all keep'),
            mock.call('ipl 00c clear'),
        ]
        self.assertListEqual(mock_s3270.string.mock_calls, call_list)

        # validate download behavior
        self.assertListEqual(mock_resp.iter_content.mock_calls, [
            mock.call(chunk_size=mock.ANY), mock.call(chunk_size=mock.ANY)])
        template_for_checking = [
            mock.call('1'),
            mock.call('2'),
            mock.call('3'),
        ]
        self.assertIn(template_for_checking, mock_file.write.mock_calls)
        self.assertListEqual(mock_s3270.transfer.mock_calls, [
            mock.call(mock_file.name,
                      zvm.HypervisorZvm.NETBOOT_KERNEL_FILE,
                      direction='send', mode='binary', timeout=600),
            mock.call(mock_file.name,
                      zvm.HypervisorZvm.NETBOOT_INITRD_FILE,
                      direction='send', mode='binary', timeout=600),
            mock.call(mock.ANY,
                      zvm.HypervisorZvm.NETBOOT_CMDLINE_FILE,
                      direction='send', mode='binary', timeout=600)
        ])
    # test_start_netboot()

    def test_start_netboot_fail_cms(self):
        """
        Exercise a netboot which fails to start CMS.
        """
        mock_outputs = []
        for entry in self._data['start_dasd']:
            pattern = ' I 1C5D'
            if re.search(pattern, entry):
                new_entry = re.sub(
                    pattern, 'HCP052E Error in CP directory', entry)
                mock_outputs.append(new_entry)
                break
            mock_outputs.append(entry)
        hyp, _ = self._patch_s3270(mock_outputs)

        # perform start
        guest_cpu = 2
        guest_memory = 2048
        iface = {"type": "osa", "id": "f5f0,f5f1,f5f2"}
        disk_dasd = {"type": "dasd", "devno": "1c5d"}
        guest_parameters = {
            "boot_method": "network",
            "storage_volumes" : [disk_dasd],
            "ifaces" : [iface],
            "netboot": {
                "cmdline": "param1=value1 param2=value2",
                "kernel_uri": "http://_install-server.com/distro/kernel.img",
                "initrd_uri": "http://_install-server.com/distro/initrd.img",
            }
        }
        hyp.login()
        with self.assertRaisesRegex(RuntimeError, 'Failed to initialize CMS'):
            hyp.start(self._user, guest_cpu, guest_memory, guest_parameters)
    # test_start_netboot_cms_fail()

    def test_start_netboot_fail_detach(self):
        """
        Try a netboot which fails to detach the existing ffff disk
        """
        orig_outputs = []
        for entry in self._data['start_dasd']:
            # strip the last steps where a disk ipl is done
            if ' I 1C5D' in entry:
                break
            orig_outputs.append(entry)
        # add the netboot steps
        orig_outputs.extend(self._data['start_netboot'])
        # replace success steps by errors
        mock_outputs = []
        pattern = 'HCPQVD040E Device FFFF does not exist'
        for entry in orig_outputs:
            if re.search(pattern, entry):
                # replace the response to return an existing dasd
                new_entry = re.sub(
                    pattern, 'DASD FFFF ON DASD', entry)
                mock_outputs.append(new_entry)
                # next response is an error after trying to detach existing
                # dasd
                new_entry = re.sub(
                    pattern, 'HCP052E Error in CP directory', entry)
                mock_outputs.append(new_entry)
                break
            mock_outputs.append(entry)
        hyp, _ = self._patch_s3270(mock_outputs)

        # perform the netboot
        guest_cpu = 2
        guest_memory = 2048
        iface = {"type": "osa", "id": "f5f0,f5f1,f5f2"}
        disk_dasd = {"type": "dasd", "devno": "1c5d"}
        guest_params = {
            "boot_method": "network",
            "storage_volumes" : [disk_dasd],
            "ifaces" : [iface],
            "netboot": {
                "cmdline": "param1=value1 param2=value2",
                "kernel_uri": "http://_install-server.com/distro/kernel.img",
                "initrd_uri": "http://_install-server.com/distro/initrd.img",
            }
        }
        hyp.login()
        with self.assertRaisesRegex(RuntimeError, 'Detach ffff failed with:'):
            hyp.start(self._user, guest_cpu, guest_memory, guest_params)

    # test_start_netboot_fail_detach()

    def test_start_netboot_fail_kernel(self):
        """
        Try a netboot which fails to load the kernel
        """
        orig_outputs = []
        for entry in self._data['start_dasd']:
            # strip the last steps where a disk ipl is done
            if ' I 1C5D' in entry:
                break
            orig_outputs.append(entry)
        # add the netboot steps
        orig_outputs.extend(self._data['start_netboot'])
        mock_outputs = []
        pattern = 'Kernel command line:'
        # replace the line where the kernel cmdline is reported
        for entry in orig_outputs:
            if re.search(pattern, entry):
                new_entry = re.sub(
                    pattern, 'DUMMY', entry)
                mock_outputs.append(new_entry)
                break
            mock_outputs.append(entry)
        hyp, mock_s3270 = self._patch_s3270(mock_outputs)

        # mock transfer calls
        mock_s3270.transfer.side_effect = 3 * [
            r'U U U C(hostname.com) I 4 24 80 0 0 0x0 0.072\n'
            r'ok\n']

        # now we need to mock the requests library to prevent an actual
        # download to happen
        patcher = patch.object(cms_module.requests, 'get', autospec=True)
        mock_get = patcher.start()
        self.addCleanup(patcher.stop)
        mock_resp = mock_get.return_value
        mock_resp.raise_for_status.return_value = None
        mock_resp.iter_content.return_value = iter(['1', '2', '3'])

        # mock temp file creation
        patcher = patch.object(cms_module, 'NamedTemporaryFile', autospec=True)
        mock_temp_cls = patcher.start()
        self.addCleanup(patcher.stop)
        mock_file = mock_temp_cls.return_value.__enter__.return_value
        mock_file.name = 'local_temp_file'

        # perform the netboot
        guest_cpu = 2
        guest_memory = 2048
        iface = {"type": "osa", "id": "f5f0,f5f1,f5f2"}
        disk_dasd = {"type": "dasd", "devno": "1c5d"}
        guest_params = {
            "boot_method": "network",
            "storage_volumes" : [disk_dasd],
            "ifaces" : [iface],
            "netboot": {
                "cmdline": "param1=value1 param2=value2",
                "kernel_uri": "http://_install-server.com/distro/kernel.img",
                "initrd_uri": "http://_install-server.com/distro/initrd.img",
            }
        }
        hyp.login()
        error_msg = 'Failed to IPL downloaded kernel'
        with self.assertRaisesRegex(RuntimeError, error_msg):
            hyp.start(self._user, guest_cpu, guest_memory, guest_params)
    # test_start_netboot_fail_kernel()

    def test_stop(self):
        """
        Exercise a normal stop command
        """
        hyp, mock_cms_cls = self._patch_cms()
        hyp.login()
        hyp.stop(self._user, None)
        mock_cms_cls.return_value.stop.assert_called_once_with()
    # test_stop()

    def test_stop_invalid(self):
        """
        Exercise invalid stop when guest name is different than username
        provided for login
        """
        hyp, _ = self._patch_cms()
        hyp.login()
        error_msg = 'guest name provided must be the same as the username'
        with self.assertRaisesRegex(ValueError, error_msg):
            hyp.stop('DUMMY', None)
    # test_stop_invalid()
# TestHypervisorZvm
