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
Implementation of hypervisor interface for Zvm
"""

#
# IMPORTS
#
from tessia_baselib.common.logger import get_logger
from tessia_baselib.common.params_validators.utils import validate_params
from tessia_baselib.common.s3270.terminal import Terminal
from tessia_baselib.hypervisors.base import HypervisorBase

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

class HypervisorZvm(HypervisorBase):
    """
    This class implements the driver to support the ZVM hypervisor type
    """

    # the identifier for this hypervisor class
    HYP_ID = 'zvm'

    @validate_params
    def __init__(self, system_name, host_name, user,
                 passwd, parameters):
        """
        Constructor

        Args:
            system_name (string): string containing the hypervisor name
            host_name (string): hostname or ip address of system
            user (string): user to login to system
            passwd (string): password to login to system
            parameters (dict): a dictionary containing values specific to each
                        hypervisor type

        Returns:
            None

        Raises:
            None
        """
        super().__init__(system_name, host_name, user,
                         passwd, parameters)

        self._logger = get_logger(__name__)

        self._logger.debug(
            "create HypervisorZvm: name='%s' host_name='%s' user='%s' "
            "parameters='%s'",
            self.name,
            self.host_name,
            self.user,
            str(self.parameters)
        )

        # initialize terminal
        self._terminal = Terminal()
    # __init__()

    def login(self, timeout=60):
        """
        Execute the login to the hypervisor system using the credentials
        provided.

        Args:
            timeout (int): how many seconds to wait for connection

        Returns:
            None

        Raises:
            None
        """
        self._logger.debug(
            "performing LOGIN HypervisorZvm: name='%s' host_name='%s' "
            "user='%s' parameters='%s'",
            self.name,
            self.host_name,
            self.user,
            str(self.parameters)
        )

        # a zVM hypervisor is also a zVM guest
        output = self._terminal.login(
            self.host_name, self.user, self.passwd, self.parameters, timeout
        )
        self._logger.debug("LOGIN process: \n"+output)
    # login()

    def logoff(self):
        """
        Close an active connection to the hypervisor system

        Args:
            None

        Returns:
            None

        Raises:
            RuntimeError: In case of fail during logoff
        """
        self._logger.debug("performing LOGOFF HypervisorZvm")

        if not self._terminal.logoff():
            self._logger.debug("Logoff failed.")
            raise RuntimeError("Could not logoff from guest.")
    # logoff()

    def start(self, guest_name, cpu, memory, parameters):
        """
        Attach the given resources and start the guest using the method
        and devices specified.

        Args:
            guest_name (str):  Name of the guest as known by hypervisor
            cpu (int):         Number of CPU's to assign.
            memory (int):      Amount of memory to assin in megabytes.
            parameters (dict): A dictionary containing values specific to each
                               hypervisor type.

        Returns:
            None

        Raises:
            NotImplementedError: as it has to be implemented by child class
        """
        raise NotImplementedError()
    # start()

    @validate_params
    def stop(self, guest_name, parameters):
        """
        Stop a given guest

        Args:
            guest_name (str): Name of the guest as known by hypervisor
            parameters (dict): Dictionary with content specific to hypervisor
                               type.

        Returns:
            None

        Raises:
            RuntimeError: In case it is not logged in, or the domain is
                          undefined or not started.
        """
        self._logger.debug(
            "performing STOP HypervisorZvm: guest_name=%s "
            "parameters=%s", guest_name, str(parameters))

        # clear system memory before logoff
        self._terminal.send_cmd("system clear", True)

        # logoff from guest
        if not self._terminal.logoff(parameters={"logoff":True}):
            self._logger.debug("Stop failed.")
            raise RuntimeError("Could not stop guest.")
    # stop()

    def reboot(self, guest_name, parameters):
        """
        Reboot a given guest

        Args:
            guest_name (str): name of the guest as known by hypervisor
            parameters (dict): content specific to hypervisor type

        Returns:
            None

        Raises:
            NotImplementedError: as it has to be implemented by child class
        """
        raise NotImplementedError()
    # reboot()
# HypervisorZvm
