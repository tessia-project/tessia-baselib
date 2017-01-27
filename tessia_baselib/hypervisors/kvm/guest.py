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
Module for GuestKvm class
"""

#
# IMPORTS
#
from tessia_baselib.hypervisors.kvm.iface import Iface
from tessia_baselib.hypervisors.kvm.storage.pool import StoragePool
from tessia_baselib.hypervisors.kvm.target_device_manager \
    import TargetDeviceManager

import os
import uuid

#
# CONSTANTS AND DEFINITIONS
#
TEMPLATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "resources/vm_template.xml")

#
# CODE
#
class GuestKvm(object):
    """
    Class abstraction for a KVM Guest
    """
    def __init__(self, guest_name, cpu, memory, parameters, host_conn):
        """
        Constructor. Initialize all instance values.

        Args:
            guest_name (str):  Name of the guest to be initiated
            cpu (int):         Number of CPUs of the guest
            memory (int):      Amount of memory used by the guest in MB
            parameters (dict):  Specific parameters for the gues
            host_conn (GuestLinux): instance connected to linux host

        Returns:
            None

        Raises:
            None
        """
        self._guest_name = guest_name
        self._cpu = cpu
        self._memory = memory
        self._parameters = parameters

        with open(TEMPLATE_FILE, "r") as template_file:
            self._template_xml = template_file.read()

        self._host_conn = host_conn
        self._target_dev_mngr = TargetDeviceManager()
        self._ifaces = []

        # get a pool to manage all disks to be used
        self._storage_pool = StoragePool(
            self._parameters.get("storage_volumes", []),
            self._target_dev_mngr,
            self._host_conn
        )
        # create an iface object for each entry in the parameters dict
        self._create_ifaces(self._parameters.get("ifaces", []))
    # __init__()

    def _create_ifaces(self, ifaces):
        """
        Auxiliar function, creates an iface object
        function.

        Args:
            ifaces (list): list of entries defined by schema
                               kvm/entities/iface_type.json
        """
        for iface_params in ifaces:
            self._ifaces.append(Iface(iface_params,
                                      self._target_dev_mngr))
    # _create_ifaces()

    def activate(self):
        """
        Activate all hardware that is used by the guest.

        Args:
            None

        Returns:
            None

        Raises:
            None
        """
        self._storage_pool.activate()
    # activate()

    def to_xml(self):
        """
        Convert all the guest properties to a domain xml format.

        Args:
            None

        Returns:
            str: a domain xml representing the guest.

        Raises:
            None
        """
        disks_xml = self._storage_pool.to_xml()

        ifaces_xml = ""
        for iface in self._ifaces:
            ifaces_xml += iface.to_xml()

        # generate a uuid for the domain xml, necessary in order to redefine
        # the domain xml while performing the network boot.
        domain_xml = self._template_xml.format(
            name=self._guest_name,
            uuid=str(uuid.uuid4()),
            memory=self._memory,
            cpu=self._cpu,
            disks=disks_xml,
            ifaces=ifaces_xml)

        return domain_xml
    # to_xml()
# GuestKvm
