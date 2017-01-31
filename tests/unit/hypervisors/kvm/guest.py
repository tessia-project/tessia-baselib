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
Test module for the guest module.
"""

#
# IMPORTS
#
from tessia_baselib.guests.linux.linux import GuestLinux
from tessia_baselib.hypervisors.kvm.guest import GuestKvm
from tessia_baselib.hypervisors.kvm.iface import Iface
from unittest import mock
from unittest import TestCase
from unittest.mock import sentinel

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
class TestGuestKvm(TestCase):
    """
    Class that provides the unit tests for the GuestKvm class.
    """
    def setUp(self):
        """
        Initialize all the mocks used in all the unit tests.
        """
        # Create the mocks of the objects that are used as parameters
        # in the instantiation of the class.
        patcher = mock.patch(
            "tessia_baselib.hypervisors.kvm.guest.TargetDeviceManager")
        self._mock_tgt_dv_mngr = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch("tessia_baselib.hypervisors.kvm.guest.Iface")
        self._mock_iface = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch("tessia_baselib.hypervisors.kvm.guest.StoragePool")
        self._mock_pool = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch("tessia_baselib.hypervisors.kvm.guest.open",
                             create=True)
        self._mock_open = patcher.start()
        self._mock_template_file = mock.Mock()
        self._mock_open.return_value.__enter__.return_value = \
            self._mock_template_file
        self.addCleanup(patcher.stop)

        self._parameters = {
            "storage_volumes": [sentinel.volume1, sentinel.volume2],
            "ifaces": [sentinel.iface1, sentinel.iface2]
        }
        # Simulates the creation of two ifaces.
        self._ifaces = [mock.Mock(spec_set=Iface), mock.Mock(spec_set=Iface)]
        self._mock_iface.side_effect = self._ifaces

        self._mock_host_conn = mock.Mock(spec_set=GuestLinux)
        # create the guest that is used in all tests
        self._guest = GuestKvm(sentinel.guest_name, sentinel.cpu,
                               sentinel.memory, self._parameters,
                               self._mock_host_conn)
    # setUp()

    def test_init(self):
        """
        Test the initial values of the instance.
        """
        self.assertIs(self._guest._guest_name, sentinel.guest_name)
        self.assertIs(self._guest._cpu, sentinel.cpu)
        self.assertIs(self._guest._memory, sentinel.memory)
        self.assertIs(self._guest._parameters, self._parameters)
        self.assertIs(self._guest._storage_pool, self._mock_pool.return_value)

        for i in range(len(self._ifaces)):
            self._mock_iface.assert_any_call(
                self._parameters.get("ifaces")[i],
                self._mock_tgt_dv_mngr.return_value)
    # test_init()

    def test_activate(self):
        """
        Test the activation procedure.
        """
        self._guest.activate()
        # Currently we only activate disks.
        self._mock_pool.return_value.activate.assert_called_with()
    # test_activate()

    @mock.patch("tessia_baselib.hypervisors.kvm.guest.uuid", spec_set=True)
    def test_to_xml(self, mock_uuid):
        """
        Test that the guest object is properly converted to xml.
        """
        self._mock_pool.return_value.to_xml.return_value = 'disk_xml1disk_xml2'

        iface_xml = "iface_xml"
        for iface in self._ifaces:
            iface.to_xml.return_value = iface_xml

        self._guest.to_xml()

        self._mock_pool.return_value.to_xml.assert_called_with()
        disk_xml = self._mock_pool.return_value.to_xml.return_value

        for iface in self._ifaces:
            iface.to_xml.assert_called_with()

        # since we have two disks and two interfaces, it is expected that
        # the content of the xml for disks and ifaces to be concatenated.
        self._mock_template_file.read.return_value.format.assert_called_with(
            name=sentinel.guest_name, uuid=str(mock_uuid.uuid4.return_value),
            memory=sentinel.memory,
            cpu=sentinel.cpu, disks=disk_xml,
            ifaces=(iface_xml+iface_xml))
    # test_to_xml()
# TestGuestKvm
