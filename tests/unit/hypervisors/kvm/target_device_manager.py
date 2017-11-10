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
Module for TestTargetDeviceManager Class
"""

#
# IMPORTS
#
from tessia.baselib.hypervisors.kvm.target_device_manager import \
    TargetDeviceManager
from unittest import mock
from unittest import TestCase

import types

#
# CONSTANTS AND DEFINITIONS
#
LETTERS = [chr(i) for i in range(ord('a'), ord('z') + 1)]

# 26 letters + space
# we are considering that a device vd_[a-z][a-z] is
# equal to vd[a-z]_[a-z]
# where _ is a empty string. This happens 26 * 26 times.
TOTAL_NUM_VALID_DEVS = ((len(LETTERS) + 1)**2 * len(LETTERS)
                        - (len(LETTERS) * len(LETTERS)))

#
# CODE
#
#
class TestTargetDeviceManager(TestCase):
    """
    Class that provides the unit tests for the TargetDevicemanager class.
    """
    def setUp(self):
        """
        Executed before the start of each test method. Creates a
        TargetDeviceManager to be used at each test.
        """
        patcher = mock.patch(
            "tessia.baselib.hypervisors.kvm.target_device_manager.ElementTree",
            autospec=True)
        self._mock_etree = patcher.start()
        self.addCleanup(patcher.stop)
        self._target_dev_mngr = TargetDeviceManager()
    # setUp()

    def test_init(self):
        """
        Test the proper initialization of the instance variables.
        """
        self.assertIs(len(self._target_dev_mngr._dev_blacklist), 0)
        self.assertIs(len(self._target_dev_mngr._devno_blacklist), 0)
        self.assertIsInstance(self._target_dev_mngr._generate_devname,
                              types.GeneratorType)
        self.assertIs(self._target_dev_mngr._next_devno, 0x0001)
    # test_init()

    def _waste_valid_devs(self, num_devices):
        """
        Auxiliary method to create a specific number of valid device
        names.
        """
        for _ in range(num_devices):
            self._target_dev_mngr.get_valid_dev()
    # _waste_valid_devs()

    def test_get_valid_dev(self):
        """
        Test that the valid devices are correctly generated.
        """
        valid_dev = self._target_dev_mngr.get_valid_dev()
        # we test the first and last valid device being generated.
        self.assertEqual(valid_dev, "vda")
        self._waste_valid_devs(TOTAL_NUM_VALID_DEVS - 2)
        valid_dev = self._target_dev_mngr.get_valid_dev()
        self.assertEqual(valid_dev, "vdzzz")
    # test_get_valid_dev()

    def test_out_of_valid_devices(self):
        """
        Test the case that there is no more valid devices available
        """
        self._waste_valid_devs(TOTAL_NUM_VALID_DEVS)
        self.assertRaisesRegex(RuntimeError, "Out of",
                               self._target_dev_mngr.get_valid_dev)
    # test_det_valid_dev_out_of_devices()

    def test_valid_dev_blacklist(self):
        """
        Test the case that a device is put in the blacklist.
        """
        self._mock_etree.fromstring.return_value.findall.return_value = [
            {"dev": "vda"}
        ]
        self.assertEqual(self._target_dev_mngr.update_dev_blacklist("somexml"),
                         "vda")
        self.assertNotEqual(self._target_dev_mngr.get_valid_dev(), "vda")
    # test_valid_dev_blacklist()

    def test_dev_already_in_blacklist(self):
        """
        Test the case that a device is already in the blacklist.
        """
        self._mock_etree.fromstring.return_value.findall.return_value = [
            {"dev": "vda"}]
        self._target_dev_mngr.update_dev_blacklist("somexml")
        self.assertRaisesRegex(ValueError, "Device vda previously",
                               self._target_dev_mngr.update_dev_blacklist,
                               "somexml")
    # test_dev_already_in_blacklist()

    def test_invalid_xml_dev_blacklist(self):
        """
        Test the case that a invalid xml was provided.
        """
        self._mock_etree.fromstring.return_value.findall.return_value = []
        self.assertRaisesRegex(ValueError, "Invalid xml",
                               self._target_dev_mngr.update_dev_blacklist,
                               "somexml")
    # test_invalid_xml_dev_blacklist()

    def test_invalid_dev_format_in_xml(self):
        """
        Test the case that there is an invalid device name in the xml.
        """
        # this is an invalid format device name.
        self._mock_etree.fromstring.return_value.findall.return_value = [
            {"dev": "vd1a"}
        ]
        self.assertRaisesRegex(ValueError, "Invalid device name",
                               self._target_dev_mngr.update_dev_blacklist,
                               "somexml")
    # test_invalid_xml_dev_blacklist()

    def test_valid_devno(self):
        """
        Test the generation of valid device numbers.
        """
        # for practical reasons, we do not test the total range here
        valid_devno = self._target_dev_mngr.get_valid_devno()
        self.assertEqual(valid_devno, "0x0001")
    # test_valid_devno()

    def test_out_of_valid_devnos(self):
        """
        Test the case when the device manager is out of valid device numbers
        """
        self._target_dev_mngr._next_devno = 0xffff
        self.assertRaisesRegex(RuntimeError, "No more device numbers",
                               self._target_dev_mngr.get_valid_devno)
    # test_out_of_valid_devnos()

    def test_devno_in_blacklist(self):
        """
        Test the case that a device number is in the blacklist.
        """
        self._mock_etree.fromstring.return_value.findall.return_value = [
            {"devno": "0x0001"}]
        self._target_dev_mngr.update_devno_blacklist("somexml")
        self.assertNotEqual(self._target_dev_mngr.get_valid_devno(),
                            "0x0001")
    # test_devno_in_blacklist()

    def test_devno_already_in_blacklist(self):
        """
        Test the case that a device number is already in blacklist.
        """
        self._mock_etree.fromstring.return_value.findall.return_value = [
            {"devno": "0x0001"}]
        self._target_dev_mngr.update_devno_blacklist("somexml")
        self.assertRaisesRegex(ValueError, "Device number 0x0001",
                               self._target_dev_mngr.update_devno_blacklist,
                               "somexml")
    # test_devno_already_in_blacklist()

    def test_invalid_xml_devno_blacklist(self):
        """
        Test the case that the xml passed to the update_devno_blacklist
        is invalid.
        """
        self._mock_etree.fromstring.return_value.findall.return_value = []

        self.assertRaisesRegex(ValueError, "Invalid xml",
                               self._target_dev_mngr.update_devno_blacklist,
                               "somexml")
    # test_invalid_xml_devno_blacklist()

    def test_invalid_devno_in_xml(self):
        """
        Test the case that the device number present in the xml is not valid.
        """
        self._mock_etree.fromstring.return_value.findall.return_value = [
            {"devno": "0x0001f"}
        ]

        self.assertRaisesRegex(ValueError, "Invalid device number",
                               self._target_dev_mngr.update_devno_blacklist,
                               "somexml")
    # test_invalid_devno_in_xml()
# TestTargetDeviceManager()
