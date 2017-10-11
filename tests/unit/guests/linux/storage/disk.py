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
Test module for disk module
"""

#
# IMPORTS
#
from tessia_baselib.common.ssh.client import SshClient
from tessia_baselib.common.ssh.shell import SshShell
from tessia_baselib.guests.linux.storage import disk as disk_module

from unittest import mock
from unittest import TestCase

#
# CONSTANTS AND DEFINITIONS
#
PARAMS_WITH_SYS_ATTRS = {
    "system_attributes": {
        "libvirt": "somexml"
    },
    "volume_id": "some_disk_id"
}

PARAMS_WITHOUT_SYS_ATTRS = {
    "volume_id": "some_disk_id"
}

#
# CODE
#


class TestDisk(TestCase):
    """
    Class that provides unit tests for the DiskBase class.
    """
    def setUp(self):
        """
        Create mocks that are used in all test cases.
        """
        # since the class is abstract we need to define a concrete child class
        # to be able to instantiate it
        class DiskConcrete(disk_module.DiskBase):
            """
            Concrete class of DiskBase
            """
            def activate(self, *args, **kwargs):
                super().activate(*args, **kwargs)
        self._disk_cls = DiskConcrete

        patcher = mock.patch.object(disk_module, 'sleep', autospec=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self._mock_host_conn = mock.Mock(spec_set=SshClient)
        self._mock_shell = mock.Mock(spec_set=SshShell)
        self._mock_host_conn.open_shell.return_value = self._mock_shell
    # setUp()

    def _create_disk(self, parameters):
        """
        Auxiliary method to create a disk.
        """
        return self._disk_cls(parameters, self._mock_host_conn)

    def test_abstract_methods(self):
        """
        Confirm that abstract methods raise NotImplementedError if called.
        """
        disk = self._create_disk(PARAMS_WITH_SYS_ATTRS)
        self.assertRaises(NotImplementedError, disk.activate)
    # test_abstract_methods()

    def test_init(self):
        """
        Test proper initialization
        """
        disk = self._create_disk(PARAMS_WITH_SYS_ATTRS)
        self.assertEqual(disk.volume_id, 'some_disk_id')
    # test_init()

    def test_enable_device(self):
        """
        Test the protected method that enable the device.
        """
        disk = self._create_disk({'volume_id': 'some_id'})
        devicenr = "some device number"

        self._mock_shell.run.side_effect = [(0, ""), (0, "")]
        disk._enable_device(devicenr)
        cmd1 = "echo free {} > /proc/cio_ignore".format(devicenr)
        cmd2 = 'chccwdev -e {}'.format(devicenr)
        calls = [mock.call(cmd1), mock.call(cmd2)]

        self.assertEqual(self._mock_shell.run.mock_calls, calls)
    # test_enable_device()

    def test_enable_device_fails(self):
        """
        Test the protected method that enable the device in the case
        it fails to be enabled.
        """
        disk = self._create_disk({'volume_id': 'some_id'})
        devicenr = "some device number"

        ret_output = [(0, "")]
        # _enable_device perform many attempts
        for _ in range(0, 6):
            ret_output.append((1, ""))
        self._mock_shell.run.side_effect = ret_output
        self.assertRaisesRegex(RuntimeError, "Failed to activate",
                               disk._enable_device, devicenr)
    # test_enable_device_fails()

# TestBaseDisk
