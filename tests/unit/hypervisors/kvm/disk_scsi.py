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
Test module for disk_scsi module
"""

#
# IMPORTS
#
from tessia_baselib.common.ssh.shell import SshShell
from tessia_baselib.hypervisors.kvm import disk_scsi
from tessia_baselib.hypervisors.kvm.disk_scsi import DiskScsi
from tessia_baselib.hypervisors.kvm.target_device_manager \
    import TargetDeviceManager
from unittest import mock
from unittest import TestCase

import copy

#
# CONSTANTS AND DEFINITIONS
#
PARAMS_SCSI = {
    "disk_type": "SCSI",
    "volume_id": "1024400000000000",
    "boot_device": True,
    "specs": {
        "multipath": True,
        "adapters": [{
            "devno": "0.0.1800",
            "wwpns": ['300607630503c1ae', '300607630503c1af']
        }, {
            "devno": "0.0.1801",
            "wwpns": ['300607630503c1ae', '300607630503c1af']
        }]
    }
}

#
# CODE
#
class TestDiskScsi(TestCase):
    """
    Class that provides the unit test for the DiskScsi class.
    """
    def setUp(self):
        """
        Create the mock objects used in the initialization of the DiskScsi.
        """
        self._mock_tgt_dv_mngr = mock.Mock(spec=TargetDeviceManager)
        self._mock_ssh_shell = mock.Mock(spec=SshShell)

        # mock timer
        self.patcher_timer = mock.patch.object(
            disk_scsi, 'timer', autospec=True)
        self.mock_timer = self.patcher_timer.start()

        # mock _enable_device method
        DiskScsi._enable_device = mock.Mock()
        self.mock_enable_device = DiskScsi._enable_device

        # mock sleep function
        self.patcher_sleep = mock.patch.object(
            disk_scsi, 'sleep', autospec=True)
        self.patcher_sleep.start()
    # setUp()

    def tearDown(self):
        """
        Stop patching the mocks. Before each test setUp will be executed and
        the patch created again.
        """
        self.patcher_timer.stop()
        #self.patcher_disk_base.stop()
        self.patcher_sleep.stop()
    # tearDown()

    def _create_disk(self, parameters):
        """
        Auxiliary method to create a disk using the mock objects.
        """
        return DiskScsi(parameters, self._mock_tgt_dv_mngr,
                        self._mock_ssh_shell)
    # _create_disk()

    def test_init(self):
        """
        Test the proper initialization the DiskScsi instance variables
        """
        disk = self._create_disk(PARAMS_SCSI)
        self.assertEqual(
            disk._lun, '0x{}'.format(PARAMS_SCSI.get("volume_id")))
        self.assertEqual(disk._multipath,
                         PARAMS_SCSI.get("specs").get("multipath"))

        check_adapters = PARAMS_SCSI.get("specs").get("adapters").copy()
        for adapter in check_adapters:
            for i in range(0, len(adapter['wwpns'])):
                adapter['wwpns'][i] = '0x{}'.format(adapter['wwpns'][i])
        self.assertEqual(disk._adapters, check_adapters)
    # test_init()

    def test_activate(self):
        """
        Test the activate method for the common case, with multipath enabled.
        """
        # The following table contais all the return values of the
        # run method, resulting from the execution of shell commands
        # to handle the disk operations.
        self._mock_ssh_shell.run.side_effect = [
            (0, ""), # _enable_zfcp_module
            # for zfcp interface 0.0.1800
            #PATH 1
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            #PATH 2
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            # for zfcp interface 0.0.1801
            #PATH 1
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            #PATH 2
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            # check_multipath
            #iteration 1
            (0, "/dev/sda"),# _get_multipath_name _get_kernel_devname
            (0, "MPATH1_UID"), # _get_multipath_name
            (0, "dm0"), #_get_dm_dev only called in the first iteration
            (0, "/dev/sda"),# _get_kernel_devname
            #iteration 2
            (0, "/dev/sdb"),# _get_multipath_name _get_kernel_devname
            (0, "MPATH1_UID"), # _get_multipath_name
            (0, "/dev/sdb"),# _get_kernel_devname
            #iteration 3
            (0, "/dev/sdc"),# _get_multipath_name _get_kernel_devname
            (0, "MPATH1_UID"), # _get_multipath_name
            (0, "/dev/sdc"),# _get_kernel_devname
            #iteration 4
            (0, "/dev/sdd"),# _get_multipath_name _get_kernel_devname
            (0, "MPATH1_UID"), # _get_multipath_name
            (0, "/dev/sdd"),# _get_kernel_devname
        ]
        disk = self._create_disk(PARAMS_SCSI)
        disk.activate()
        # one call for each zfcp adapter
        self.assertEqual(self.mock_enable_device.call_count, 2)
    # test_activate()

    def test_activate_new_wwpn_port_type(self):
        """
        Test the activation of the disk using the port_rescan sysfs interface
        for the wwpns.
        """
        self._mock_ssh_shell.run.side_effect = [
            (0, ""), # _enable_zfcp_module
            #PATH 1
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (1, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            #PATH 2
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (1, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            #PATH 1
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (1, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            #PATH 2
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (1, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            # check_multipath
            #iteration 1
            (0, "/dev/sda"),# _get_multipath_name _get_kernel_devname
            (0, "MPATH1_UID"), # _get_multipath_name
            (0, "dm0"), #_get_dm_dev only called in the first iteration
            (0, "/dev/sda"),# _get_kernel_devname
            #iteration 2
            (0, "/dev/sdb"),# _get_multipath_name _get_kernel_devname
            (0, "MPATH1_UID"), # _get_multipath_name
            (0, "/dev/sdb"),# _get_kernel_devname
            #iteration 3
            (0, "/dev/sdc"),# _get_multipath_name _get_kernel_devname
            (0, "MPATH1_UID"), # _get_multipath_name
            (0, "/dev/sdc"),# _get_kernel_devname
            #iteration 4
            (0, "/dev/sdd"),# _get_multipath_name _get_kernel_devname
            (0, "MPATH1_UID"), # _get_multipath_name
            (0, "/dev/sdd"),# _get_kernel_devname
        ]
        disk = self._create_disk(PARAMS_SCSI)
        disk.activate()
    # test_activate_new_wwpn_port_type()

    def test_activate_fail_activate_lun(self):
        """
        Test the case that a lun fails to be activated.
        """
        self._mock_ssh_shell.run.side_effect = [
            (0, ""), # _enable_zfcp_module
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (1, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (1, "") # _enable_lun_paths _activate_lun (raise Exception if 1)
        ]
        disk = self._create_disk(PARAMS_SCSI)
        self.assertRaisesRegex(RuntimeError, "Failed to activate LUN",
                               disk.activate)
    # test_activate_fail_activate_lun()

    def test_activate_fail2_activate_lun(self):
        """
        Test the case that a lun fails to be activated.
        """
        self._mock_ssh_shell.run.side_effect = [
            (0, ""), # _enable_zfcp_module
            #PATH 1
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (1, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            (0, "") # _enable_lun_paths _activate_lun (raise Exception if 1)
        ]
        self.mock_timer.side_effect = [None, None, RuntimeError]
        disk = self._create_disk(PARAMS_SCSI)
        self.assertRaisesRegex(RuntimeError, "up after adding LUN",
                               disk.activate)
    # test_activate_fail2_activate_lun()

    def test_activate_fail_add_lun(self):
        """
        Test the case that a lun fails to be add.
        """
        self._mock_ssh_shell.run.side_effect = [
            (0, ""), # _enable_zfcp_module
            #PATH 1
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (1, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            (0, "1") # _enable_lun_paths _activate_lun (raise Exception if 1)
        ]
        self.mock_timer.side_effect = [None, None, RuntimeError]
        disk = self._create_disk(PARAMS_SCSI)
        self.assertRaisesRegex(RuntimeError, "Failed to add",
                               disk.activate)
    # test_activate_fail_add_lun()

    def test_activate_multipath_name_not_same(self):
        """
        Test the case in which two paths don't belong to the same multipath
        name.
        """
        self._mock_ssh_shell.run.side_effect = [
            (0, ""), # _enable_zfcp_module
            #PATH 1
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            #PATH 2
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            #PATH 1
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            #PATH 2
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            # check_multipath
            #iteration 1
            (0, "/dev/sda"),# _get_kernel_devname
            (0, "/dev/sda"),# _get_multipath_name _get_kernel_devname
            (0, "PATH1_UID"), # _get_multipath_name
            (0, "dm0"), #_get_dm_dev only called in the first iteration
            #iteration 2
            (0, "/dev/sdb"),# _get_kernel_devname
            (0, "/dev/sdb"),# _get_multipath_name _get_kernel_devname
            (0, "MPATH2_UID") # _get_multipath_name
        ]
        disk = self._create_disk(PARAMS_SCSI)
        self.assertRaisesRegex(RuntimeError, "Multipath map",
                               disk.activate)
    # test_activate_multipath_name_not_same()

    def test_activate_multipath_not_available(self):
        """
        Test the case that a path does not belong to a multipath name.
        """
        self._mock_ssh_shell.run.side_effect = [
            (0, ""), # _enable_zfcp_module
            #PATH 1
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            #PATH 2
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            #PATH 1
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            #PATH 2
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            # check_multipath
            #iteration 1
            (0, "/dev/sda"),# _get_multipath_name _get_kernel_devname
            (0, ""), # _get_multipath_name trial 0
            (0, ""), # _get_multipath_name trial 1
            (0, ""), # _get_multipath_name trial 5
            (0, ""), # _get_multipath_name trial 15
            (0, ""), # _get_multipath_name trial 30
            (0, ""), # _get_multipath_name trial 60
        ]
        disk = self._create_disk(PARAMS_SCSI)
        self.assertRaisesRegex(RuntimeError, "Multipath map not available",
                               disk.activate)
    # test_activate_multipath_not_available()

    def test_activate_fail_determine_dev_mapper(self):
        """
        Test the case in which the device mapper is not available.
        """
        self._mock_ssh_shell.run.side_effect = [
            (0, ""), # _enable_zfcp_module
            #(0, ""), # _enable_lun_paths _enable_device
            #(0, ""),
            #PATH 1
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            #PATH 2
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            #PATH 1
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            #PATH 2
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            # check_multipath
            #iteration 1
            (0, "/dev/sda"),# _get_multipath_name _get_kernel_devname
            (0, "PATH1_UID"), # _get_multipath_name
            (1, ""), #_get_dm_dev only called in the first iteration trial 0
            (1, ""), #_get_dm_dev only called in the first iteration trial 1
            (1, ""), #_get_dm_dev only called in the first iteration trial 5
            (1, ""), #_get_dm_dev only called in the first iteration trial 15
            (1, ""), #_get_dm_dev only called in the first iteration trial 30
            (1, "") #_get_dm_dev only called in the first iteration trial 60
        ]
        disk = self._create_disk(PARAMS_SCSI)
        self.assertRaisesRegex(RuntimeError, "Failed to determine",
                               disk.activate)
    # test_activate_fail_determine_dev_mapper()

    def test_activate_disable_multipath(self):
        """
        Test the case that the multipath is disabled.
        """
        params_scsi_no_multipath = copy.deepcopy(PARAMS_SCSI)
        params_scsi_no_multipath.get("specs")["multipath"] = False
        self._mock_ssh_shell.run.side_effect = [
            (0, ""), # _enable_zfcp_module
            #(0, ""), # _enable_lun_paths _enable_device
            #(0, ""),
            #PATH 1
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            #PATH 2
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            #PATH 1
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            #PATH 2
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            # _disable_multipath
            (0, ""), # _disable_multipath _get_kernel_devname Path 1
            (0, ""), # _disable_multipath _get_kernel_devname Path 2
            (0, ""), # _disable_multipath _get_kernel_devname Path 3
            (0, ""), # _disable_multipath _get_kernel_devname Path 4
        ]
        disk = self._create_disk(params_scsi_no_multipath)
        disk.activate()
    # test_activate_disable_multipath()

    def test_activate_fail_fcp(self):
        """
        Test the case that the zfcp module fails to be loaded.
        """
        disk = self._create_disk(PARAMS_SCSI)
        self._mock_ssh_shell.run.side_effect = [(1, "")]
        self.assertRaisesRegex(RuntimeError, "Unable to load fcp",
                               disk.activate)
    # test_activate_fail_fcp()
# TestDiskScsi