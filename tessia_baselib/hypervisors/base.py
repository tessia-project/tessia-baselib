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
Defines the interface for hypervisor classes
"""

#
# IMPORTS
#
import abc

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

class HypervisorBase(metaclass=abc.ABCMeta):
    """
    This is the abstract Hypervisor class which defines the interface to be
    implemented by each hypervisor driver
    """

    # the identifier for this hypervisor class, should be a lowercase string
    HYP_ID = 'base'

    def __init__(self, system_name, host_name, user,
                 passwd, parameters):
        """
        Constructor

        Args:
            system_name (str): string containing the hypervisor name
            host_name (str): hostname or ip address of system
            user (str): user to login to system
            passwd (str): password to login to system
            parameters (dict): content specific to each hypervisor type.

        Returns:
            None

        Raises:
            None
        """
        # store instance values
        self.name = system_name
        self.host_name = host_name
        self.user = user
        self.passwd = passwd
        self.parameters = parameters

    # __init__()

    @abc.abstractmethod
    def login(self, timeout=60):
        """
        Execute the login to the hypervisor system using the credentials
        provided.

        Args:
            timeout (int): how many seconds to wait for connection

        Returns:
            string 'ok' if succeded, error message otherwise

        Raises:
            NotImplementedError: as it has to be implemented by child class
        """
        raise NotImplementedError()
    # login()

    @abc.abstractmethod
    def logoff(self):
        """
        Close an active connection to the hypervisor system

        Args:
            None

        Returns:
            string 'ok' if succeded, error message otherwise

        Raises:
            NotImplementedError: as it has to be implemented by child class
        """
        raise NotImplementedError()
    # logoff()

    @abc.abstractmethod
    def start(self, guest_name, cpu, memory, parameters):
        """
        Attach the given resources and start the guest using the method
        and devices specified. Returns 'ok' if succeded, error message
        otherwise

        Args:
            guest_name (str): name of the guest as known by hypervisor
            cpu (int): number of CPU's to assign
            memory (int): amount of memory to assin in megabytes
            parameters (dict): content specfic to each hypervisor type

        Returns:
            None

        Raises:
            NotImplementedError: as it has to be implemented by child class
        """
        raise NotImplementedError()
    # start()

    @abc.abstractmethod
    def stop(self, guest_name, parameters):
        """
        Stop a given guest. Returns 'ok' if succeded, error message otherwise

        Args:
            guest_name (str): name of the guest as known by hypervisor
            parameters (dict):  content specific to hypervisor type

        Returns:
            None

        Raises:
            NotImplementedError: as it has to be implemented by child class
        """
        raise NotImplementedError()
    # stop()

    @abc.abstractmethod
    def reboot(self, guest_name, parameters):
        """
        Reboot a given guest

        Args:
            guest_name (str): name of the guest as known by hypervisor
            parameters (dict): content specific to hypervisor type

        Returns:
            string 'ok' if succeded, error message otherwise

        Raises:
            NotImplementedError: as it has to be implemented by child class
        """
        raise NotImplementedError()
    # stop()
# HypervisorBase
