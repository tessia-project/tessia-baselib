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
import os

#
# CONSTANTS AND DEFINITIONS
#
TEMPLATE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "resources/{}_template.xml")

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

        Raises:
            ValueError: in case an invalid network type is specified
        """
        self._parameters = parameters

        attributes = self._parameters.get("attributes")
        self._libvirt_xml = attributes.get("libvirt")
        if self._libvirt_xml is not None:
            target_dev_mngr.update_devno_blacklist(self._libvirt_xml)
            return

        template_path = TEMPLATE_FILE.format(self._parameters['type'].lower())
        if not os.path.exists(template_path):
            raise ValueError('Unknown interface type {}'.format(
                self._parameters['type']))

        with open(template_path, "r") as template_fd:
            xml_template = template_fd.read()

        devno = target_dev_mngr.get_valid_devno()

        self._libvirt_xml = xml_template.format(
            mac=self._parameters['mac_address'],
            hostiface=attributes['hostiface'],
            devno=devno
        )
    # __init__()

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
