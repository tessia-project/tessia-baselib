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
Module for the Disk Class
"""

#
# IMPORTS
#
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
    def __init__(self, parameters, target_dev_mngr, cmd_channel):
        """
        Constructor. Initialize instance variables.
        Args:
            parameters (dict): Disk parameters as defined in the json schema.
            target_dev_mngr (object): Instance of TargetDeviceManager.
            cmd_channel (object):     An object that provides a method in the
                                      format "run(self, cmd, timeout=120):".
                                      This method is used to perform commands
                                      in the host in order to handle disk
                                      operations.

        Returns:
            None

        Raises:
            None
        """
        self._parameters = parameters

        self._libvirt_xml = None
        self._target_dev = None
        self._target_devno = None
        # the _source_dev variable is set in the implementations of
        # DiskBase.
        self._source_dev = None

        system_attributes = self._parameters.get("system_attributes")
        # The domain xml for this device might be passed in the parameters
        if system_attributes is not None:
            # the libvirt property will always exists since it is
            # required in the jsonschema.
            self._libvirt_xml = system_attributes.get("libvirt")
            #if the devices are already in the blacklist an exception will
            #be raised.
            self._target_dev = (target_dev_mngr.
                                update_dev_blacklist(self._libvirt_xml))
            self._target_devno = (target_dev_mngr.
                                  update_devno_blacklist(self._libvirt_xml))
        else:
            #get a dynamic generated device and device number
            self._target_dev = target_dev_mngr.get_valid_dev()
            self._target_devno = target_dev_mngr.get_valid_devno()
        self._cmd_channel = cmd_channel
    # __init__()

    def _enable_device(self, devicenr):
        """
        Enable a device in the ccw bus.

        Args:
            devicenr (str): device number of the device to be enabled

        Returns:
            None

        Raises:
            RuntimeError: In case the command fails to be executed
        """
        # make sure device is not in cio_ignore list
        self._cmd_channel.run("echo free {} >"
                              " /proc/cio_ignore".format(devicenr))

        # try to activate channel again
        ret, output = self._cmd_channel.run('chccwdev -e {}'.format(devicenr))
        if ret != 0:
            raise RuntimeError("Failed to activate "
                               "device devicenr={}: {}".format(devicenr,
                                                               output))
    # _enable_device()

    def activate(self):
        """
        Activate the disk by performing all necessary operations to get
        the block device avaiable in the hypervisor operating system.

        Args:
            None

        Returns:
            None

        Raises:
            NotImplementedError: In case the method is not implemented.
        """
        raise NotImplementedError()
    # attach()

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

        if self._libvirt_xml is None:
            template_file = open(TEMPLATE_FILE, "r").read()

            boot_tag = ""
            if self._parameters.get("boot_device"):
                boot_tag = '<boot order="1"/>'

            self._libvirt_xml = (
                template_file.format(dev=self._source_dev,
                                     target_dev=self._target_dev,
                                     devno=self._target_devno,
                                     boot_tag=boot_tag))
        return self._libvirt_xml
    # to_xml()
#DiskBase
