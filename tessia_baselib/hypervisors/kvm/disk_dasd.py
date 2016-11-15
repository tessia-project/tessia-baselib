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
Module for class DiskDasd
"""
#
# IMPORTS
#
from tessia_baselib.common.logger import get_logger
from tessia_baselib.common.utils import timer
from tessia_baselib.hypervisors.kvm.disk import DiskBase

#
# CONSTANTS AND DEFINITIONS
#
DASD_DEVPATH = "/dev/disk/by-path/ccw-0.0."

#
# CODE
#
class DiskDasd(DiskBase):
    """
    This class is an abstraction for a dasd disk.
    """
    def __init__(self, parameters, target_dev_mngr, cmd_channel):
        """
        Constructor

        Args:
            parameters (dict):  Disk parameters as defined in the json schema.
            target_dev_mngr (object): Instance of TargetDeviceManager.
            cmd_channel (object): An object that provides a method in the
                                  format "run(self, cmd, timeout=120):".
                                  This method is used to perform commands in
                                  the host ir order to handledisk operations.

        Returns:
            None

        Raises:
            None
        """
        super().__init__(parameters, target_dev_mngr, cmd_channel)

        self._logger = get_logger(__name__)

        self._devicenr = self._parameters.get("volume_id")
        self._devicenr = self._devicenr.replace("0x", "")

        self._logger.debug("Creating DiskDasd: devicenr=%s", self._devicenr)
    # __init__()

    def activate(self):
        """
        Activate the disk by performing the proper handling.

        Args:
            None

        Returns:
            None

        Raises:
            None
        """
        self._logger.debug("Activating dasd disk "
                           "devicenr=%s", self._devicenr)

        check_cmd = "readlink -e '{}{}'".format(DASD_DEVPATH, self._devicenr)
        ret, _ = self._cmd_channel.run(check_cmd)

        if ret != 0:

            self._logger.debug("Dasd disk devicenr=%s not attached yed."
                               "Trying to attach.", self._devicenr)
            # for dasd we just need to enable the channel
            self._enable_device(self._devicenr)

            # check if it is really activated
            error_msg = 'Failed to enable device {}'.format(
                self._devicenr)
            timer(self._cmd_channel, check_cmd, [0, 1, 5, 15], error_msg)

        self._logger.debug("DiskDasd devicenr=%s attached.",
                           self._devicenr)

        # update the source device path
        self._source_dev = DASD_DEVPATH + self._devicenr
    # attach()
# DiskDasd
