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
from tessia_baselib.hypervisors.kvm.storage import disk as disk_module
from tessia_baselib.hypervisors.kvm.target_device_manager \
    import TargetDeviceManager

from unittest import mock
from unittest import TestCase

#
# CONSTANTS AND DEFINITIONS
#
PARAMS_WITH_SYS_ATTRS = {
    "system_attributes": {
        "libvirt": "somexml"
    },
    "volume_id": "some_disk_id",
    "hyp_dev_path": "/dev/sda"
}

PARAMS_WITHOUT_SYS_ATTRS = {
    "volume_id": "some_disk_id",
    "hyp_dev_path": "/dev/sda"
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
        self._mock_tgt_dv_mngr = mock.Mock(spec=TargetDeviceManager)
    # setUp()

    def _create_disk(self, parameters):
        """
        Auxiliary method to create a disk.
        """
        return disk_module.DiskBase(parameters, self._mock_tgt_dv_mngr)
    # _create_disk()

    def test_init_with_system_attrs(self):
        """
        Test the case that the disk is initiated with parameters
        containing a system_attributes properties.
        """
        disk = self._create_disk(PARAMS_WITH_SYS_ATTRS)

        self.assertIs(disk._parameters, PARAMS_WITH_SYS_ATTRS)
        system_attributes = PARAMS_WITH_SYS_ATTRS.get("system_attributes")
        self.assertIs(disk._libvirt_xml, system_attributes.get("libvirt"))
        self._mock_tgt_dv_mngr.update_dev_blacklist.assert_called_once_with(
            system_attributes.get("libvirt"))
        self._mock_tgt_dv_mngr.update_devno_blacklist.assert_called_once_with(
            system_attributes.get("libvirt"))
        self.assertIs(disk._target_dev,
                      self._mock_tgt_dv_mngr.update_dev_blacklist.return_value)
        self.assertIs(
            disk._target_devno,
            self._mock_tgt_dv_mngr.update_devno_blacklist.return_value
        )
    # test_init_with_system_attrs()

    def test_init_without_system_attrs(self):
        """
        Test the case that the disk is initiated with parameters
        not containing a system_attributes properties.
        """
        disk = self._create_disk(PARAMS_WITHOUT_SYS_ATTRS)

        self.assertIs(disk._parameters, PARAMS_WITHOUT_SYS_ATTRS)
        self._mock_tgt_dv_mngr.get_valid_dev.assert_called_once_with()
        self._mock_tgt_dv_mngr.get_valid_devno.assert_called_once_with()
        self.assertIs(disk._target_dev,
                      self._mock_tgt_dv_mngr.get_valid_dev.return_value)
        self.assertIs(disk._target_devno,
                      self._mock_tgt_dv_mngr.get_valid_devno.return_value)
    # test_init_without_system_attrs()

    def test_to_xml_with_libvirt_xml(self):
        """
        Test the case that a libvirt xml is provided to the disk.
        """
        disk = self._create_disk(PARAMS_WITH_SYS_ATTRS)

        system_attrs = PARAMS_WITH_SYS_ATTRS.get("system_attributes")
        self.assertIs(system_attrs.get("libvirt"), disk.to_xml())
    # test_to_xml_with_libvirt_xml()

    @mock.patch("tessia_baselib.hypervisors.kvm.storage.disk.open",
                create=True)
    def test_to_xml_read_template(self, mock_open):
        """
        Test the case that the libvirt xml is not provided and must
        be generated.
        """
        disk = self._create_disk(PARAMS_WITHOUT_SYS_ATTRS)
        template_file = mock_open().__enter__.return_value.read.return_value

        self.assertIs(
            disk.to_xml(),
            template_file.format.return_value)

        template_file.format.assert_called_with(
            dev=PARAMS_WITHOUT_SYS_ATTRS['hyp_dev_path'],
            target_dev=self._mock_tgt_dv_mngr.get_valid_dev.return_value,
            devno=self._mock_tgt_dv_mngr.get_valid_devno.return_value,
            boot_tag="")
    # test_to_xml_reading_template()

    @mock.patch("tessia_baselib.hypervisors.kvm.storage.disk.open",
                create=True)
    def test_to_xml_read_template_with_boot_tag(self, mock_open):
        """
        Test the case that the libvirt xml is not provided and must
        be generated. Also, the disk is a boot_device
        """
        params = {
            'boot_device': True,
            'volume_id': 'some_id',
            'hyp_dev_path': '/dev/mapper/mpath_1',
        }
        disk = self._create_disk(params)
        template_file = mock_open().__enter__.return_value.read.return_value

        self.assertIs(
            disk.to_xml(),
            template_file.format.return_value)

        template_file.format.assert_called_with(
            dev=params['hyp_dev_path'],
            target_dev=self._mock_tgt_dv_mngr.get_valid_dev.return_value,
            devno=self._mock_tgt_dv_mngr.get_valid_devno.return_value,
            boot_tag='<boot order="1"/>')
    # test_to_xml_read_template_with_boot_tag()

    def test_init_missing_dev_path(self):
        """
        Test the case where the device path is missing in the provided disk
        parameters.
        """
        params = {
            'boot_device': True,
            'volume_id': 'some_id',
        }
        msg = 'Device path on hypervisor not provided'
        with self.assertRaisesRegex(ValueError, msg):
            self._create_disk(params)
    # test_init_missing_dev_path()
# TestBaseDisk
