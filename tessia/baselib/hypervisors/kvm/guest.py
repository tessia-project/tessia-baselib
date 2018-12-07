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
from tessia.baselib.hypervisors.kvm.iface import Iface
from tessia.baselib.hypervisors.kvm.storage.pool import StoragePool
from tessia.baselib.hypervisors.kvm.target_device_manager \
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
class GuestKvm:
    """
    Class abstraction for a KVM Guest
    """
    def __init__(self, guest_name, cpu, memory, parameters, guest_linux):
        """
        Constructor. Initialize all instance values.

        Args:
            guest_name (str):  Name of the guest to be initiated
            cpu (int):         Number of CPUs of the guest
            memory (int):      Amount of memory used by the guest in MB
            parameters (dict):  Specific parameters for the gues
            guest_linux (GuestLinux): linux host

        Raises:
            None
        """
        self._guest_name = guest_name
        self._cpu = cpu
        self._memory = memory
        self._parameters = parameters

        with open(TEMPLATE_FILE, "r") as template_file:
            self._template_xml = template_file.read()

        self._guest_obj = guest_linux

        # set by activate()
        self._active_hw = None
    # __init__()

    def activate(self):
        """
        Activate all hardware that is used by the guest.

        Args:
            None

        Raises:
            None
        """
        self._active_hw = self._guest_obj.hotplug(
            vols=self._parameters.get("storage_volumes", []))
    # activate()

    def to_xml(self):
        """
        Convert all the guest properties to a domain xml format.

        Args:
            None

        Returns:
            str: a domain xml representing the guest.

        Raises:
            RuntimeError: if called before hardware activation
        """
        if self._active_hw is None:
            raise RuntimeError('Guest hardware must be activated first')

        target_dev_mngr = TargetDeviceManager()

        # use a pool to manage xml configuration of the disks
        storage_pool = StoragePool(
            self._parameters.get("storage_volumes", []),
            self._active_hw['vols'],
            target_dev_mngr,
        )
        disks_xml = storage_pool.to_xml()

        # create an iface object for each entry in the parameters dict
        ifaces_xml = ""
        for iface_params in self._parameters.get("ifaces", []):
            iface_obj = Iface(iface_params, target_dev_mngr)
            ifaces_xml += iface_obj.to_xml()

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
