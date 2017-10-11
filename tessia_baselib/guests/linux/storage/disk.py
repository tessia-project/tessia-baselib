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
import abc

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
class DiskBase(metaclass=abc.ABCMeta):
    """
    Base class for all type of physical disks.
    """
    def __init__(self, parameters, host_conn):
        """
        Constructor. Initialize instance variables.

        Args:
            parameters (dict): Disk parameters as defined in the json schema.
            host_conn (SshClient): instance connected to linux host

        Raises:
            None
        """
        self._parameters = parameters

        # useful to uniquely identify the instance
        self.volume_id = self._parameters['volume_id']

        # shell object to run commands on hypervisor, each disk gets its own
        self._cmd_channel = host_conn.open_shell()

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
        self._cmd_channel.run("echo free {} > /proc/cio_ignore"
                              .format(devicenr))

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
            raise RuntimeError("Failed to activate device devicenr={}: {}"
                               .format(devicenr, output))
    # _enable_device()

    @abc.abstractmethod
    def activate(self):
        """
        Activate the disk by performing all necessary operations to get
        the block device available in the hypervisor operating system.
        Concrete implementation should return the disk's device path on
        the filesystem.

        Args:
            None

        Raises:
            NotImplementedError: as it has to be implemented by children
                                 classes
        """
        raise NotImplementedError()
    # activate()
# DiskBase
