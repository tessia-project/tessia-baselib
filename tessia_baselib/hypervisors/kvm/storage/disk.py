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
Module for the Disk Class
"""

#
# IMPORTS
#
from time import sleep
import os

#
# CONSTANTS AND DEFINITIONS
#
TEMPLATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "resources/disk_template.xml")

#
# CODE
#
class DiskBase(object):
    """
    Base class for all type of physical disks.
    """
    def __init__(self, parameters, target_dev_mngr, host_conn):
        """
        Constructor. Initialize instance variables.

        Args:
            parameters (dict): Disk parameters as defined in the json schema.
            target_dev_mngr (TargetDeviceManager): object instance
            host_conn (GuestLinux): instance connected to linux host

        Raises:
            None
        """
        self._parameters = parameters
        # useful to uniquely identify the instance
        self.volume_id = self._parameters['volume_id']

        # xml device definition
        self._libvirt_xml = None
        # template used to create the xml device definition
        with open(TEMPLATE_FILE, "r") as template_fd:
            self._xml_template = template_fd.read()
        # shell object to run commands on hypervisor, each disk gets its own
        self._cmd_channel = host_conn.open_session()

        # the _source_dev variable is set by the concrete classes
        self._source_dev = None

        system_attributes = self._parameters.get("system_attributes")
        # device xml definition was passed in the parameters: use it to define
        # the target's devname and devno
        if system_attributes is not None:
            # the libvirt property will always exist in 'system_attributes' as
            # it is required in the jsonschema.
            self._libvirt_xml = system_attributes.get("libvirt")

            # if the devices are already in the blacklist an exception will
            # be raised.
            self._target_dev = target_dev_mngr.update_dev_blacklist(
                self._libvirt_xml)
            self._target_devno = target_dev_mngr.update_devno_blacklist(
                self._libvirt_xml)

        # no xml specified: get a dynamic generated device and device number
        else:
            self._target_dev = target_dev_mngr.get_valid_dev()
            self._target_devno = target_dev_mngr.get_valid_devno()

    # __init__()

    def _enable_device(self, devicenr):
        """
        Enable a device in the ccw bus.

        Args:
            devicenr (str): device number of the device to be enabled

        Raises:
            RuntimeError: In case the command fails to be executed
        """
        # make sure device is not in cio_ignore list
        self._cmd_channel.run("echo free {} >"
                              " /proc/cio_ignore".format(devicenr))

        # try to activate channel again
        active = False
        for time in (0, 1, 5, 15, 30, 60):
            sleep(time)
            ret, output = self._cmd_channel.run(
                'chccwdev -e {}'.format(devicenr))
            if ret == 0:
                active = True
                break
        if not active:
            raise RuntimeError("Failed to activate "
                               "device devicenr={}: {}".format(devicenr,
                                                               output))
    # _enable_device()

    def activate(self):
        """
        Activate the disk by performing all necessary operations to get
        the block device available in the hypervisor operating system.

        Args:
            None

        Raises:
            NotImplementedError: as it has to be implemented by children
                                 classes
        """
        raise NotImplementedError()
    # activate()

    def to_xml(self):
        """
        Convert the disk to a libvirt domain xml disk.
        This function must be called after the activation of the device.

        Args:
            None

        Returns:
            str: a xml representing a disk device

        Raises:
            RuntimeError: if the device is not activated.
        """
        if self._source_dev is None:
            raise RuntimeError("The disk is not activated")

        # definition already provided or built: return it
        if self._libvirt_xml is not None:
            return self._libvirt_xml

        # build the libvirt definition
        boot_tag = ""
        if self._parameters.get("boot_device"):
            boot_tag = '<boot order="1"/>'

        self._libvirt_xml = (
            self._xml_template.format(
                dev=self._source_dev,
                target_dev=self._target_dev,
                devno=self._target_devno,
                boot_tag=boot_tag)
        )
        return self._libvirt_xml
    # to_xml()
# DiskBase
