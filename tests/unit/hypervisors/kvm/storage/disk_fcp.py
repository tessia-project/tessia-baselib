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
Test module for disk_fcp module
"""

#
# IMPORTS
#
from tessia_baselib.guests.linux.linux import GuestLinux
from tessia_baselib.guests.linux.linux_session import GuestSessionLinux
from tessia_baselib.hypervisors.kvm.storage import disk_fcp
from tessia_baselib.hypervisors.kvm.storage.disk_fcp import DiskFcp
from tessia_baselib.hypervisors.kvm.target_device_manager \
    import TargetDeviceManager
from unittest import mock
from unittest import TestCase

import copy

#
# CONSTANTS AND DEFINITIONS
#
PARAMS_FCP = {
    "type": "FCP",
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
class TestDiskFcp(TestCase):
    """
    Class that provides the unit test for the DiskFcp class.
    """
    def setUp(self):
        """
        Create the mock objects used in the initialization of the DiskFcp.
        """
        self._mock_tgt_dv_mngr = mock.Mock(spec=TargetDeviceManager)
        self._mock_host_conn = mock.Mock(spec_set=GuestLinux)
        self._mock_session = mock.Mock(spec_set=GuestSessionLinux)
        self._mock_host_conn.open_session.return_value = self._mock_session

        # mock timer
        patcher = mock.patch.object(
            disk_fcp, 'timer', autospec=True)
        self.mock_timer = patcher.start()
        self.addCleanup(patcher.stop)

        # mock _enable_device method
        DiskFcp._enable_device = mock.Mock()
        self.mock_enable_device = DiskFcp._enable_device

        # mock sleep function
        patcher = mock.patch.object(
            disk_fcp, 'sleep', autospec=True)
        patcher.start()
        self.addCleanup(patcher.stop)
    # setUp()

    def _create_disk(self, parameters):
        """
        Auxiliary method to create a disk using the mock objects.
        """
        return DiskFcp(parameters, self._mock_tgt_dv_mngr,
                       self._mock_host_conn)
    # _create_disk()

    def test_init(self):
        """
        Test the proper initialization the DiskFcp instance variables
        """
        disk = self._create_disk(PARAMS_FCP)
        self.assertEqual(
            disk._lun, '0x{}'.format(PARAMS_FCP.get("volume_id")))
        self.assertEqual(disk._multipath,
                         PARAMS_FCP.get("specs").get("multipath"))

        check_adapters = PARAMS_FCP.get("specs").get("adapters").copy()
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
        self._mock_session.run.side_effect = [
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
        disk = self._create_disk(PARAMS_FCP)
        disk.activate()
        # one call for each zfcp adapter
        self.assertEqual(self.mock_enable_device.call_count, 2)
    # test_activate()

    def test_activate_new_wwpn_port_type(self):
        """
        Test the activation of the disk using the port_rescan sysfs interface
        for the wwpns.
        """
        self._mock_session.run.side_effect = [
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
        disk = self._create_disk(PARAMS_FCP)
        disk.activate()
    # test_activate_new_wwpn_port_type()

    def test_activate_fail_activate_lun(self):
        """
        Test the case that a lun fails to be activated.
        """
        self._mock_session.run.side_effect = [
            (0, ""), # _enable_zfcp_module
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (1, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (1, "") # _enable_lun_paths _activate_lun (raise Exception if 1)
        ]
        disk = self._create_disk(PARAMS_FCP)
        self.assertRaisesRegex(RuntimeError, "Failed to activate LUN",
                               disk.activate)
    # test_activate_fail_activate_lun()

    def test_activate_fail2_activate_lun(self):
        """
        Test the case that a lun fails to be activated.
        """
        self._mock_session.run.side_effect = [
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
        disk = self._create_disk(PARAMS_FCP)
        self.assertRaisesRegex(RuntimeError, "up after adding LUN",
                               disk.activate)
    # test_activate_fail2_activate_lun()

    def test_activate_fail_add_lun(self):
        """
        Test the case that a lun fails to be add.
        """
        self._mock_session.run.side_effect = [
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
        disk = self._create_disk(PARAMS_FCP)
        self.assertRaisesRegex(RuntimeError, "Failed to add",
                               disk.activate)
    # test_activate_fail_add_lun()

    def test_activate_multipath_name_not_same(self):
        """
        Test the case in which two paths don't belong to the same multipath
        name.
        """
        self._mock_session.run.side_effect = [
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
        disk = self._create_disk(PARAMS_FCP)
        self.assertRaisesRegex(RuntimeError, "Multipath map",
                               disk.activate)
    # test_activate_multipath_name_not_same()

    def test_activate_multipath_not_available(self):
        """
        Test the case that a path does not belong to a multipath name.
        """
        self._mock_session.run.side_effect = [
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
        disk = self._create_disk(PARAMS_FCP)
        self.assertRaisesRegex(RuntimeError, "Multipath map not available",
                               disk.activate)
    # test_activate_multipath_not_available()

    def test_activate_fail_determine_dev_mapper(self):
        """
        Test the case in which the device mapper is not available.
        """
        self._mock_session.run.side_effect = [
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
        disk = self._create_disk(PARAMS_FCP)
        self.assertRaisesRegex(RuntimeError, "Failed to determine",
                               disk.activate)
    # test_activate_fail_determine_dev_mapper()

    def test_activate_disable_multipath(self):
        """
        Test the case that the multipath is disabled.
        """
        params_fcp_no_multipath = copy.deepcopy(PARAMS_FCP)
        params_fcp_no_multipath.get("specs")["multipath"] = False
        self._mock_session.run.side_effect = [
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
        disk = self._create_disk(params_fcp_no_multipath)
        disk.activate()
    # test_activate_disable_multipath()

    def test_activate_fail_fcp(self):
        """
        Test the case that the zfcp module fails to be loaded.
        """
        disk = self._create_disk(PARAMS_FCP)
        self._mock_session.run.side_effect = [(1, "")]
        self.assertRaisesRegex(RuntimeError, "Unable to load fcp",
                               disk.activate)
    # test_activate_fail_fcp()
# TestDiskFcp
