# Copyright 2026 IBM Corp.
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
Module for class DiskQcow2
"""

#
# IMPORTS
#
from tessia.baselib.common.logger import get_logger
from tessia.baselib.guests.linux.storage.disk import DiskBase

#
# CONSTANTS AND DEFINITIONS
#
QCOW2_IMAGE_SIZE = "40G"
#
# CODE
#
class DiskQcow2(DiskBase):
    """
    Disk implementation for qcow2-backed KVM guests (KVMA).
    """

    def __init__(self, parameters, host_conn):
        """
        Constructor

        Args:
            parameters (dict): Disk parameters as defined in json schema.
            host_conn (GuestLinux): instance
        """
        super().__init__(parameters, host_conn)

        self._logger = get_logger(__name__)

        self._image_path = self._parameters['system_attributes']['path']

        self._logger.debug(
            "Creating DiskQcow2: image=%s size=%s",
            self._image_path,
            QCOW2_IMAGE_SIZE
        )

    # __init__()

    def activate(self):
        """
        Create qcow2 image and return file path.

        Returns:
            str: qcow2 image path

        Raises:
            RuntimeError: If qcow2 image creation fails.
        """
        create_cmd = (
            f"qemu-img create -f qcow2 "
            f"{self._image_path} {QCOW2_IMAGE_SIZE}"
        )
        ret, output = self._cmd_channel.run(create_cmd)

        if ret != 0:
            raise RuntimeError(
                f"Failed to create qcow2 image {self._image_path}: {output}"
            )

        self._logger.debug("DiskQcow2 image created: %s", self._image_path)

        # return file qcow2 path
        return self._image_path
