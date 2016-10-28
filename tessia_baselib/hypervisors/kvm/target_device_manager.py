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
Module for TargetDeviceManager class
"""

#
# IMPORTS
#
from xml.etree import ElementTree

import re
#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

class TargetDeviceManager(object):
    """
    This class manage the device names and device numbers used in a KVM
    guest so that only valid information is generated. Duplication is
    avoided and detected.
    """
    def __init__(self):
        """
        Constructor. Initialize instance variables.

        Args:
            None

        Returns:
            None

        Raises:
            None
        """
        self._dev_blacklist = []
        self._devno_blacklist = []
        self._valid_devs = TargetDeviceManager._valid_devs_generator()
        self._next_devno = 0x0001
    # __init__()

    @staticmethod
    def _valid_devs_generator():
        """
        Auxiliary generator used to generate valid virtio device names.
        """
        letters = [chr(i) for i in range(ord('a'), ord('z') + 1)]

        for i in [''] + letters:
            for j in [''] + letters:
                for k in letters:
                    yield "vd{}{}{}".format(i, j, k)
    # _valid_devs_generator()

    def _generate_devno(self):
        """
        Auxiliary function to generate a device number. The device
        numbers are generated incrementally.

        Args:
            None

        Returns:
            str: the next device number available.

        Raises:
            RuntimeError: If there is no more device numbers available.
        """
        if self._next_devno == 0xffff:
            raise RuntimeError("No more device numbers available.")
        devno = "0x{:04x}".format(self._next_devno)
        self._next_devno += 1

        return devno
    # _generate_devno()

    def get_valid_dev(self):
        """
        Get the next valid virtio device name.

        Args:
            None

        Returns:
            str: the next valid device name.

        Raises:
            RuntimeError: In case there is no more device available.
        """

        try:
            valid_dev = next(self._valid_devs)
            # generate device names until not in blacklist
            while valid_dev in self._dev_blacklist:
                valid_dev = next(self._valid_devs)
        except StopIteration:
            raise RuntimeError("Out of valid devices")
        self._dev_blacklist.append(valid_dev)
        return valid_dev
    # get_valid_dev()

    def get_valid_devno(self):
        """
        Get the next valid virtio device number.

        Args:
            None

        Returns:
            str: the next valid device number.

        Raises:
            None
        """
        valid_devno = self._generate_devno()

        while valid_devno in self._devno_blacklist:
            valid_devno = self._generate_devno()

        self._devno_blacklist.append(valid_devno)

        return valid_devno
    # get_valid_devno()

    def update_dev_blacklist(self, xml):
        """
        Update the blacklist of used device names by reading the libvirt
        xml.

        Args:
            xml (str): The libvirt xml of the device.

        Returns:
            str: Device that was included in the blacklist.

        Raises:
            ValueError: In case the device name contained in the xml
                        is already present in the blacklist or the xml
                        does not have a target tag.
        """
        root = ElementTree.fromstring(xml)
        targets = root.findall("target")

        if len(targets) != 1:
            raise ValueError("Invalid xml")

        dev = targets[0].get("dev")

        if re.match("^vd[a-z]{1,3}$", dev) is None:
            raise ValueError("Invalid device name in xml")

        if dev in self._dev_blacklist:
            raise ValueError("Device {} "
                             "previously defined".format(dev))

        self._dev_blacklist.append(dev)

        return dev
    # update_dev_blacklist()

    def update_devno_blacklist(self, xml):
        """
        Update the blacklist of used device numbers by reading the libvirt
        xml.

        Args:
            xml (str): The libvirt xml of the device.

        Returns:
            str: Device number that was included in the blacklist.

        Raises:
            ValueError: In case the device number contained in the xml
                        is already present in the blacklist or the xml
                        does not have a target tag.
        """
        root = ElementTree.fromstring(xml)
        addresses = root.findall("address")

        if len(addresses) != 1:
            raise ValueError("Invalid xml")

        devno = addresses[0].get("devno")

        if re.match('^0x[0-9a-f]{4}$', devno) is None:
            raise ValueError("Invalid device number in the xml")

        if devno in self._devno_blacklist:
            raise ValueError("Device number {} "
                             "previously defined".format(devno))

        self._devno_blacklist.append(devno)

        return devno
    # update_devno_blacklist()
# TargetDeviceManager
