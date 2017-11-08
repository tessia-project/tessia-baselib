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
from copy import deepcopy
from tessia.baselib.common import utils
from tessia.baselib.common.ssh.client import SshClient
from tessia.baselib.common.ssh.shell import SshShell
from tessia.baselib.guests.linux.storage import disk_fcp
from unittest import mock
from unittest import TestCase

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
        self._mock_host_conn = mock.Mock(spec_set=SshClient)
        self._mock_shell = mock.Mock(spec_set=SshShell)
        self._mock_host_conn.open_shell.return_value = self._mock_shell

        # mock sleep in timer
        patcher = mock.patch.object(utils, 'sleep', autospec=True)
        patcher.start()
        self.addCleanup(patcher.stop)

        # mock sleep in disk module
        patcher = mock.patch.object(disk_fcp, 'sleep', autospec=True)
        patcher.start()
        self.addCleanup(patcher.stop)
    # setUp()

    def _create_disk(self, parameters):
        """
        Auxiliary method to create a disk using the mock objects.
        """
        return disk_fcp.DiskFcp(parameters, self._mock_host_conn)
    # _create_disk()

    @staticmethod
    def _get_outputs_for_mpath():
        """
        Return the list of command outputs expected for a normal path
        activation up to the point where multipath checking/disabling starts.
        """
        # The following table contais all the return values of the
        # run method, resulting from the execution of shell commands
        # to handle the disk operations.
        outputs = [
            (0, ""), # _enable_zfcp_module
            # for zfcp interface 0.0.1800
            #PATH 1
            (0, ""), # _enable_device echo free cio_ignore
            (0, ""), # _enable_device chccwdev -e
            (0, ""), # _check_adapter_active
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            # _enable_lun_paths _activate_lun _get_scsi_dev_filename
            (0, "0.0.1800/0x300607630503c1ae/0x1024400000000000 "
                "1:0:23:1073889314"),
            (0, "/dev/sda"),

            #PATH 2
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            # _enable_lun_paths _activate_lun _get_scsi_dev_filename
            (0, "0.0.1800/0x300607630503c1af/0x1024400000000000 "
                "1:0:23:1073889315"),
            (0, "/dev/sdb"),

            # for zfcp interface 0.0.1801
            #PATH 1
            (0, ""), # _enable_device echo free cio_ignore
            (0, ""), # _enable_device chccwdev -e
            (0, ""), # _check_adapter_active
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            # _enable_lun_paths _activate_lun _get_scsi_dev_filename
            (0, "0.0.1801/0x300607630503c1ae/0x1024400000000000 "
                "1:0:24:1073889317"),
            (0, "/dev/sdc"),

            #PATH 2
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_wwpn
            (0, ""), # _enable_lun_paths _activate_wwpn
            (1, ""), # _enable_lun_paths _is_lun_active 0 = True, 1 = False
            (0, ""), # _enable_lun_paths _activate_lun (raise Exception if 1)
            # _enable_lun_paths _activate_lun _get_scsi_dev_filename
            (0, "0.0.1801/0x300607630503c1af/0x1024400000000000 "
                "1:0:24:1073889315"),
            (0, "/dev/sdd"),

            # check_multipath
            # _get_all_scsi_dev_filenames
            (0, "0.0.1800/0x300607630503c1ae/0x1024400000000000 "
                "1:0:23:1073889314"),
            (0, "/dev/sda"),
            (0, "0.0.1800/0x300607630503c1af/0x1024400000000000 "
                "1:0:23:1073889315"),
            (0, "/dev/sdb"),
            (0, "0.0.1801/0x300607630503c1ae/0x1024400000000000 "
                "1:0:24:1073889317"),
            (0, "/dev/sdc"),
            (0, "0.0.1801/0x300607630503c1af/0x1024400000000000 "
                "1:0:24:1073889315"),
            (0, "/dev/sdd"),
        ]
        return outputs
    # _get_outputs_for_mpath()

    def test_init(self):
        """
        Test the proper initialization the DiskFcp instance variables
        """
        disk = self._create_disk(PARAMS_FCP)
        self.assertEqual(
            disk._lun, '0x{}'.format(PARAMS_FCP.get("volume_id")))
        self.assertEqual(disk._multipath,
                         PARAMS_FCP.get("specs").get("multipath"))

        check_adapters = deepcopy(PARAMS_FCP.get("specs").get("adapters"))
        for adapter in check_adapters:
            for i in range(0, len(adapter['wwpns'])):
                adapter['wwpns'][i] = '0x{}'.format(adapter['wwpns'][i])
        self.assertEqual(disk._adapters, check_adapters)
    # test_init()

    def test_activate(self):
        """
        Test the activate method for the common case, with multipath enabled.
        """
        mpath_id = "MPATH1_UID"
        outputs = self._get_outputs_for_mpath()
        outputs.extend([
            # check_multipath
            #iteration 1
            (0, "/dev/sda"),# _get_multipath_name _get_kernel_devname
            (0, mpath_id), # _get_multipath_name
            #iteration 2
            (0, "/dev/sdb"),# _get_multipath_name _get_kernel_devname
            (0, mpath_id), # _get_multipath_name
            #iteration 3
            (0, "/dev/sdc"),# _get_multipath_name _get_kernel_devname
            (0, mpath_id), # _get_multipath_name
            #iteration 4
            (0, "/dev/sdd"),# _get_multipath_name _get_kernel_devname
            (0, mpath_id), # _get_multipath_name
        ])
        self._mock_shell.run.side_effect = outputs
        disk = self._create_disk(PARAMS_FCP)

        # validate response containing the device path
        self.assertEqual(disk.activate(), '/dev/mapper/{}'.format(mpath_id))
    # test_activate()

    def test_activate_new_wwpn_port_type(self):
        """
        Test the activation of the disk using the port_rescan sysfs interface
        for the wwpns.
        """
        self._mock_shell.run.side_effect = [
            (0, ""), # _enable_zfcp_module
            #PATH 1
            (0, ""), # _enable_device echo free cio_ignore
            (0, ""), # _enable_device chccwdev -e
            (0, ""), # _check_adapter_active
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (1, ""), # _enable_lun_paths _activate_wwpn -e port_add
            (0, ""), # _enable_lun_paths _activate_wwpn -e port_rescan && echo
            (0, ""), # _enable_lun_paths _activate_wwpn -e adapter/wwpn
            (1, ""), # _enable_lun_paths _is_lun_active _get_scsi_dev_filename
            (0, ""), # _enable_lun_paths _activate_lun echo > unit_add
            # _enable_lun_paths _activate_lun _get_scsi_dev_filename
            (0, "0.0.1800/0x300607630503c1ae/0x1024400000000000 "
                "1:0:23:1073889314"),
            (0, "/dev/sda"),

            #PATH 2
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (1, ""), # _enable_lun_paths _activate_wwpn -e port_add
            (0, ""), # _enable_lun_paths _activate_wwpn -e port_rescan && echo
            (0, ""), # _enable_lun_paths _activate_wwpn -e adapter/wwpn
            (1, ""), # _enable_lun_paths _is_lun_active _get_scsi_dev_filename
            (0, ""), # _enable_lun_paths _activate_lun echo > unit_add
            # _enable_lun_paths _activate_lun _get_scsi_dev_filename
            (0, "0.0.1800/0x300607630503c1af/0x1024400000000000 "
                "1:0:23:1073889315"),
            (0, "/dev/sdb"),

            #PATH 1
            (0, ""), # _enable_device echo free cio_ignore
            (0, ""), # _enable_device chccwdev -e
            (0, ""), # _check_adapter_active
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (1, ""), # _enable_lun_paths _activate_wwpn -e port_add
            (0, ""), # _enable_lun_paths _activate_wwpn -e port_rescan && echo
            (0, ""), # _enable_lun_paths _activate_wwpn -e adapter/wwpn
            (1, ""), # _enable_lun_paths _is_lun_active _get_scsi_dev_filename
            (0, ""), # _enable_lun_paths _activate_lun echo > unit_add
            # _enable_lun_paths _activate_lun _get_scsi_dev_filename
            (0, "0.0.1801/0x300607630503c1ae/0x1024400000000000 "
                "1:0:24:1073889317"),
            (0, "/dev/sdc"),

            #PATH 2
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (1, ""), # _enable_lun_paths _activate_wwpn -e port_add
            (0, ""), # _enable_lun_paths _activate_wwpn -e port_rescan && echo
            (0, ""), # _enable_lun_paths _activate_wwpn -e adapter/wwpn
            (1, ""), # _enable_lun_paths _is_lun_active _get_scsi_dev_filename
            (0, ""), # _enable_lun_paths _activate_lun echo > unit_add
            # _enable_lun_paths _activate_lun _get_scsi_dev_filename
            (0, "0.0.1801/0x300607630503c1af/0x1024400000000000 "
                "1:0:24:1073889315"),
            (0, "/dev/sdd"),

            # check_multipath
            # _get_all_scsi_dev_filenames
            (0, "0.0.1800/0x300607630503c1ae/0x1024400000000000 "
                "1:0:23:1073889314"),
            (0, "/dev/sda"),
            (0, "0.0.1800/0x300607630503c1af/0x1024400000000000 "
                "1:0:23:1073889315"),
            (0, "/dev/sdb"),
            (0, "0.0.1801/0x300607630503c1ae/0x1024400000000000 "
                "1:0:24:1073889317"),
            (0, "/dev/sdc"),
            (0, "0.0.1801/0x300607630503c1af/0x1024400000000000 "
                "1:0:24:1073889315"),
            (0, "/dev/sdd"),

            #iteration 1
            (0, "/dev/sda"),# _get_multipath_name _get_kernel_devname
            (0, "MPATH1_UID"), # _get_multipath_name
            #iteration 2
            (0, "/dev/sdb"),# _get_multipath_name _get_kernel_devname
            (0, "MPATH1_UID"), # _get_multipath_name
            #iteration 3
            (0, "/dev/sdc"),# _get_multipath_name _get_kernel_devname
            (0, "MPATH1_UID"), # _get_multipath_name
            #iteration 4
            (0, "/dev/sdd"),# _get_multipath_name _get_kernel_devname
            (0, "MPATH1_UID"), # _get_multipath_name
        ]
        disk = self._create_disk(PARAMS_FCP)
        self.assertEqual(disk.activate(), '/dev/mapper/MPATH1_UID')
    # test_activate_new_wwpn_port_type()

    def test_activate_fail_unit_add(self):
        """
        Test the case that a lun fails to be activated due to failed unit_add
        operation.
        """
        output = [
            (0, ""), # _enable_zfcp_module
            #PATH 1
            (0, ""), # _enable_device echo free cio_ignore
            (0, ""), # _enable_device chccwdev -e
            (0, ""), # _check_adapter_active
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (1, ""), # _enable_lun_paths _activate_wwpn -e port_add
            (0, ""), # _enable_lun_paths _activate_wwpn -e port_rescan && echo
            (0, ""), # _enable_lun_paths _activate_wwpn -e adapter/wwpn
            (1, ""), # _enable_lun_paths _is_lun_active _get_scsi_dev_filename
            (1, ""), # _enable_lun_paths _activate_lun unit_add
        ]
        self._mock_shell.run.side_effect = output
        disk = self._create_disk(PARAMS_FCP)
        self.assertRaisesRegex(RuntimeError, "Failed to activate LUN",
                               disk.activate)
    # test_activate_fail_unit_add()

    def test_activate_fail_no_path_cat_fail(self):
        """
        Test the case where a lun fails to be activated after unit_add
        works and the path does not come up. This variant also simulates
        a failure to check for the 'failed' file.
        """
        output = [
            (0, ""), # _enable_zfcp_module
            #PATH 1
            (0, ""), # _enable_device echo free cio_ignore
            (0, ""), # _enable_device chccwdev -e
            (0, ""), # _check_adapter_active
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (1, ""), # _enable_lun_paths _activate_wwpn -e port_add
            (0, ""), # _enable_lun_paths _activate_wwpn -e port_rescan && echo
            (0, ""), # _enable_lun_paths _activate_wwpn -e adapter/wwpn
            (1, ""), # _enable_lun_paths _is_lun_active _get_scsi_dev_filename
            (0, ""), # _enable_lun_paths _activate_lun unit_add
        ]
        # _get_scsi_dev_filename many attempts
        for _ in range(0, 6):
            output.append((1, ""))
        output.append((1, "")) # _enable_lun_paths _activate_lun cat failed
        self._mock_shell.run.side_effect = output
        disk = self._create_disk(PARAMS_FCP)
        self.assertRaisesRegex(RuntimeError, "didn't come up after adding LUN",
                               disk.activate)
    # test_activate_fail_unit_add()

    def test_activate_fail_no_path_cat_success(self):
        """
        Test the case where a lun fails to be activated after unit_add
        works and the path does not come up. In this variant the 'failed'
        provides a hint about wrong storage configuration.
        """
        output = [
            (0, ""), # _enable_zfcp_module
            #PATH 1
            (0, ""), # _enable_device echo free cio_ignore
            (0, ""), # _enable_device chccwdev -e
            (0, ""), # _check_adapter_active
            (1, ""), # _enable_lun_paths _is_wwpn_active 0 = True, 1 = False
            (1, ""), # _enable_lun_paths _activate_wwpn -e port_add
            (0, ""), # _enable_lun_paths _activate_wwpn -e port_rescan && echo
            (0, ""), # _enable_lun_paths _activate_wwpn -e adapter/wwpn
            (1, ""), # _enable_lun_paths _is_lun_active _get_scsi_dev_filename
            (0, ""), # _enable_lun_paths _activate_lun unit_add
        ]
        # _get_scsi_dev_filename many attempts
        for _ in range(0, 6):
            output.append((1, ""))
        output.append((0, "1")) # _enable_lun_paths _activate_lun cat failed
        self._mock_shell.run.side_effect = output
        disk = self._create_disk(PARAMS_FCP)
        re_msg = "Failed to add .* check your storage configuration"
        self.assertRaisesRegex(RuntimeError, re_msg, disk.activate)
    # test_activate_fail_add_lun()

    def test_activate_multipath_name_not_same(self):
        """
        Test the case in which two paths don't belong to the same multipath
        name.
        """
        outputs = self._get_outputs_for_mpath()
        outputs.extend([
            # check_multipath
            #iteration 1
            (0, "/dev/sda"),# _get_multipath_name _get_kernel_devname
            (0, "PATH1_UID"), # _get_multipath_name
            #iteration 2
            (0, "/dev/sdb"),# _get_multipath_name _get_kernel_devname
            (0, "MPATH2_UID") # _get_multipath_name
        ])
        self._mock_shell.run.side_effect = outputs
        disk = self._create_disk(PARAMS_FCP)
        self.assertRaisesRegex(RuntimeError, "Multipath map",
                               disk.activate)
    # test_activate_multipath_name_not_same()

    def test_activate_multipath_not_available(self):
        """
        Test the case that a path does not belong to a multipath name.
        """
        outputs = self._get_outputs_for_mpath()
        outputs.extend([
            # check_multipath
            #iteration 1
            (0, "/dev/sda"),# _get_multipath_name _get_kernel_devname
            (0, ""), # _get_multipath_name trial 0
            (0, ""), # _get_multipath_name trial 1
            (0, ""), # _get_multipath_name trial 5
            (0, ""), # _get_multipath_name trial 15
            (0, ""), # _get_multipath_name trial 30
            (0, ""), # _get_multipath_name trial 60
        ])
        self._mock_shell.run.side_effect = outputs
        disk = self._create_disk(PARAMS_FCP)
        self.assertRaisesRegex(RuntimeError, "Multipath map not available",
                               disk.activate)
    # test_activate_multipath_not_available()

    def test_activate_disable_multipath(self):
        """
        Test the case that the multipath is disabled.
        """
        params_fcp_no_multipath = deepcopy(PARAMS_FCP)
        params_fcp_no_multipath.get("specs")["multipath"] = False
        outputs = self._get_outputs_for_mpath()
        outputs.extend([
            # _disable_multipath
            (0, ""), # _disable_multipath _get_kernel_devname Path 1
            (0, ""), # _disable_multipath _get_kernel_devname Path 2
            (0, ""), # _disable_multipath _get_kernel_devname Path 3
            (0, ""), # _disable_multipath _get_kernel_devname Path 4
        ])
        self._mock_shell.run.side_effect = outputs
        disk = self._create_disk(params_fcp_no_multipath)
        self.assertEqual(disk.activate(), '/dev/sda')
    # test_activate_disable_multipath()

    def test_activate_fail_fcp(self):
        """
        Test the case that the zfcp module fails to be loaded.
        """
        disk = self._create_disk(PARAMS_FCP)
        self._mock_shell.run.side_effect = [(1, "")]
        self.assertRaisesRegex(RuntimeError, "Unable to load fcp",
                               disk.activate)
    # test_activate_fail_fcp()

    def test_no_fcp_path(self):
        """
        Test the case where no fcp path was provided in disk parameters.
        """
        params = {
            "type": "FCP",
            "volume_id": "1024400000000000",
            "boot_device": True,
            "specs": {
                "multipath": True,
                "adapters": [{
                    "devno": "0.0.1800",
                }, {
                    "devno": "0.0.1801",
                }]
            }
        }
        msg = 'No FCP path defined for disk LUN 0x{}'.format(
            params['volume_id'])
        with self.assertRaisesRegex(ValueError, msg):
            self._create_disk(params)
    # test_no_fcp_path()
# TestDiskFcp
