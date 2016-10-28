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
Module for Iface class
"""

#
# IMPORTS
#

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

class Iface(object):
    """
    Abstraction for a network Interfaces
    """
    def __init__(self, parameters, target_dev_mngr):
        """
        Constructor. Initialize instance variables.

        Args:
            parameters (dict): Interface parameters as defined in the
                               json schema.
            target_dev_mngr (object):  Instance of TargetDeviceManager class.

        Returns:
            None

        Raises:
            None
        """
        self._parameters = parameters

        attributes = self._parameters.get("attributes")
        self._libvirt_xml = attributes.get("libvirt")

        target_dev_mngr.update_devno_blacklist(self._libvirt_xml)
    # __init__

    def to_xml(self):
        """
        Convert the interface to a libvirt domain xml interface.

        Args:
            None

        Returns:
            str: a xml representing a disk device

        Raises:
            None
        """
        return self._libvirt_xml
    # to_xml()
# Iface
