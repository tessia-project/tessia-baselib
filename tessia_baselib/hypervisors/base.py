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

#
# IMPORTS
#

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

class HypervisorBase(object):
    """
    This is the abstract Hypervisor class which defines the interface to be
    implemented by each hypervisor driver
    """

    # the identifier for this hypervisor class, should be a lowercase string
    hyp_id = 'base'

    def __init__(self, logger, system_name, host_name, user,
                 passwd, extensions):
        """
        Constructor

        Args:
            logger: logging object
            system_name: string containing the hypervisor name
            host_name: hostname or ip address of system
            user: user to login to system
            passwd: password to login to system
            extensions: a dictionary containing values specific to each
                        hypervisor type

        Returns:
            None

        Raises:
            None
        """
        # store instance values
        self.logger = logger
        self.name = system_name
        self.host_name = host_name
        self.user = user
        self.passwd = passwd
        self.extensions = extensions

    # __init__()

    def login(self, timeout=60):
        """
        Execute the login to the hypervisor system using the credentials
        provided.

        Args:
            timeout: how many seconds to wait for connection

        Returns:
            string 'ok' if succeded, error message otherwise

        Raises:
            None
        """
        raise NotImplementedError()
    # login()

    def logoff(self):
        """
        Close an active connection to the hypervisor system

        Args:
            None

        Returns:
            string 'ok' if succeded, error message otherwise

        Raises:
            None
        """
        raise NotImplementedError()
    # logoff()

    def start(self, guest_name, resources, boot_method, boot_device,
              extensions):
        """
        Attach the given resources and start the guest using the method
        and devices specified.

        Args:
            guest_name: name of the guest as known by hypervisor
            resources: dictionary containing the resources to attach
            boot_method: one of 'disk' or 'network'
            boot_device: the disk name (for disk method) or uri (for network
                         method)
            extensions: dictionary with content specific to hypervisor type

        Returns:
            string 'ok' if succeded, error message otherwise

        Raises:
            None
        """
        raise NotImplementedError()
    # start()

    def stop(self, guest_name, extensions):
        """
        Stop a given guest

        Args:
            guest_name: name of the guest as known by hypervisor
            extensions: dictionary with content specific to hypervisor type

        Returns:
            string 'ok' if succeded, error message otherwise

        Raises:
            None
        """
        raise NotImplementedError()
    # stop()

# HypervisorBase
