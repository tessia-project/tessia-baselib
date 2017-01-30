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
Test module for iface module.
"""

#
# IMPORTS
#
from tessia_baselib.hypervisors.kvm.iface import Iface
from tessia_baselib.hypervisors.kvm.target_device_manager \
    import TargetDeviceManager
from unittest import mock
from unittest import TestCase

#
# CONSTANTS AND DEFINITIONS
#
IFACE_PARAMS = {
    "attributes": {
        "libvirt": "some xml"
    }
}

#
# CODE
#
class TestIface(TestCase):
    """
    Class for testing of Ifaces.
    """
    def setUp(self):
        """
        Setup and create mock objects used in the tests.
        """
        self._mock_tgt_dv_mngr = mock.Mock(spec=TargetDeviceManager)
    # setUp()

    def _create_iface(self, parameters):
        """
        Auxiliary method to create a iface.
        """
        return Iface(parameters, self._mock_tgt_dv_mngr)
    # _create_iface()

    def test_init_invalid_type(self):
        """
        Test the case where an invalid interface type is specified.
        """
        iface_params = {
            'attributes': {'hostiface': 'eth0'},
            'mac_address': 'aa:bb:cc:dd:ee:ff',
            'type': 'invalid',
        }
        with self.assertRaises(ValueError):
            self._create_iface(iface_params)
    # test_init_invalid_type()

    def test_to_xml(self):
        """
        Test iface creation with a xml provided as parameter.
        """
        iface = self._create_iface(IFACE_PARAMS)

        # validate proper initialization
        self.assertIs(iface._libvirt_xml,
                      IFACE_PARAMS.get("attributes").get("libvirt"))
        self.assertIs(iface._parameters, IFACE_PARAMS)
        self._mock_tgt_dv_mngr.update_devno_blacklist.assert_called_with(
            IFACE_PARAMS.get("attributes").get("libvirt"))

        # validate the xml provided was used
        iface = self._create_iface(IFACE_PARAMS)
        self.assertIs(iface.to_xml(),
                      IFACE_PARAMS.get("attributes").get("libvirt"))
    # test_to_xml()

    @mock.patch("tessia_baselib.hypervisors.kvm.iface.open",
                create=True)
    def test_to_xml_read_template(self, mock_open):
        """
        Test the case that the libvirt xml is not provided and must
        be generated.
        """
        template_file = mock_open().__enter__.return_value.read.return_value
        iface_params = {
            'attributes': {'hostiface': 'eth0'},
            'mac_address': 'aa:bb:cc:dd:ee:ff',
            'type': 'MACVTAP',
        }
        iface = self._create_iface(iface_params)

        self.assertIs(
            iface.to_xml(),
            template_file.format.return_value)

        template_file.format.assert_called_with(
            mac=iface_params['mac_address'],
            devno=self._mock_tgt_dv_mngr.get_valid_devno.return_value,
            hostiface=iface_params['attributes']['hostiface'])
    # test_to_xml_reading_template()
# TestIface
