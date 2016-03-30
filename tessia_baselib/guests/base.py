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

class GuestBase(object):
    """
    This is the abstract Guest class which defines the interface to be
    implemented by each guest driver
    """

    # the identifier for this guest class, should be a lowercase string
    guest_id = 'base'

    def __init__(self, logger, system_name, host_name, user,
                 passwd, extensions):
        """
        Constructor

        Args:
            logger: logging object
            system_name: string containing the guest name
            host_name: hostname or ip address of system
            user: user to login to system
            passwd: password to login to system
            extensions: a dictionary containing values specific to each
                        guest type

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
        Execute the login to the guest system using the credentials
        provided.

        Args:
            timeout: how many seconds to wait for connection

        Returns:
            string 'ok' if succeeded, error message otherwise

        Raises:
            None
        """
        raise NotImplementedError()
    # login()

    def logoff(self):
        """
        Close an active connection to the guest system

        Args:
            None

        Returns:
            string 'ok' if succeeded, error message otherwise

        Raises:
            None
        """
        raise NotImplementedError()
    # logoff()

    def stop(self):
        """
        Stop a given guest by executing a shutdown command

        Args:
            None

        Returns:
            string 'ok' if succeeded, error message otherwise

        Raises:
            None
        """
        raise NotImplementedError()
    # stop()

# GuestBase
