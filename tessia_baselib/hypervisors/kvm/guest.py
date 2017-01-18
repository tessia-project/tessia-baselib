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
from tessia_baselib.hypervisors.kvm.storage.disk_dasd import DiskDasd
from tessia_baselib.hypervisors.kvm.storage.disk_fcp import DiskFcp
from tessia_baselib.hypervisors.kvm.iface import Iface
from tessia_baselib.hypervisors.kvm.target_device_manager \
    import TargetDeviceManager

import os
import uuid

#
# CONSTANTS AND DEFINITIONS
#
DISK_TYPEMAP = {
    "DASD": DiskDasd,
    "FCP": DiskFcp
}

TEMPLATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "resources/vm_template.xml")


#
# CODE
#

def create_disk(parameters, target_dev_mngr, cmd_channel):
    """
    Factory function for disks

    Args:
        parameters (str):  Dictionary containing the definitions for
                           the specific disk type. A disk_type property
                           must be provided in this dictionary.
        target_dev_mngr (object): An instance of a TargetDeviceManager that is
                                  used to manage the device numbers and device
                                  names.
        cmd_channel (object): An object that provides a method in the format
                              "run(self, cmd, timeout=120):". This method is
                              used to perform commands in the host ir order
                              to handle the disk.
    Returns:
        object: An disk object instantiated.

    Raises:
        RuntimeError: In case the disk_type is not recognized.

    """
    disk_type = parameters["disk_type"]

    if disk_type not in DISK_TYPEMAP.keys():
        raise RuntimeError("Invalid or unknown disk_type")

    return DISK_TYPEMAP[disk_type](parameters, target_dev_mngr, cmd_channel)

class GuestKvm(object):
    """
    Class abstraction for a KVM Guest
    """
    def __init__(self, guest_name, cpu, memory, parameters, cmd_channel):
        """
        Constructor. Initialize all instance values.

        Args:
            guest_name (str):  Name of the guest to be initiated
            cpu (int):         Number of CPUs of the guest
            memory (int):      Amount of memory used by the guest in MB
            parameters (dict):  Specific parameters for the gues
            cmd_channel (object): An object that provides a method in the
                                  format "run(cmd, timeout=120)".
                                  This method is used to perform commands
                                  in the host ir order to handle all the
                                  hardware configuration.

        Returns:
            None

        Raises:
            None
        """
        self._guest_name = guest_name
        self._cpu = cpu
        self._memory = memory
        self._parameters = parameters
        self._cmd_channel = cmd_channel

        self._target_dev_mngr = TargetDeviceManager()

        self._disks = []
        self._virt_disks = []
        self._ifaces = []

        with open(TEMPLATE_FILE, "r") as template_file:
            self._template_xml = template_file.read()

        # create a disk object for each entry in the parameters dict
        self._create_disks(self._parameters.get("storage_volumes", []))
        # create an iface object for each entry in the parameters dict
        self._create_ifaces(self._parameters.get("ifaces", []))
    # __init__()

    # _create_boot_params()

    def _create_disks(self, vols):
        """
        Auxiliar function, creates a disk object using the appropriate factory
        function.

        Args:
            vols (list): list of entries defined by schema
                         common/entities/disk_type.json
        """
        for disk_params in vols:
            self._disks.append(create_disk(disk_params, self._target_dev_mngr,
                                           self._cmd_channel))
    # _create_disks()

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
        for disk in self._disks:
            disk.activate()
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
        disks_xml = ""
        for disk in self._disks:
            disks_xml += disk.to_xml()

        ifaces_xml = ""
        for iface in self._ifaces:
            ifaces_xml += iface.to_xml()

        # generate the uuid of the domain xml, necessary to redefine the
        # domain xml while performing the network boot.
        uuid_str = str(uuid.uuid4())
        return self._template_xml.format(name=self._guest_name,
                                         uuid=uuid_str,
                                         memory=self._memory,
                                         cpu=self._cpu,
                                         disks=disks_xml,
                                         ifaces=ifaces_xml)
    # to_xml()
# GuestKvm
