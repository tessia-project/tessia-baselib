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
from tessia_baselib.common.logger import getLogger
from tessia_baselib.common.ssh.client import SshClient
from tessia_baselib.guests.base import GuestBase
from tessia_baselib.guests.linux.distros import generic as genericModule
from tessia_baselib.guests.linux.distros import DISTRO_MODULES
from tessia_baselib.guests.linux.linux_session import GuestSessionLinux

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

class GuestLinux(GuestBase):
    """
    This class implement the support to the linux guest type. It uses ssh for
    communication with the target system and delegates distro specific tasks
    (like package management) to a distro object instantiated upon login
    according to the environment found.
    """

    # the identifier for this guest class, should be a lowercase string
    GUEST_ID = 'linux'

    def __init__(self, system_name, host_name, user, passwd, extensions):
        """
        Constructor, store instance values via base class and initialize logger

        Args:
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
        # base class will store instances values
        super().__init__(
            system_name,
            host_name,
            user,
            passwd,
            extensions
        )

        # initialize logger object
        self._loggerObj = getLogger(__name__)

        # ssh connection to be initialized by login()
        self._sshConn = None

        # distro class to use, will be determined by login()
        self._distroObj = None

        # log object creation for debugging
        self._loggerObj.debug(
            "create GuestLinux: name='%s' host_name='%s' user='%s' "
            "extensions='%s'",
            self.name,
            self.host_name,
            self.user,
            str(self.extensions)
        )
    # __init__()

    def hotplug(self, method, resources, extensions):
        """
        Hotplug/unplug a given dictionary of resources to/from the guest.

        Args:
            method: attach (hotplug) or detach (hotunplug)
            resources: dict in the form:
                       {'cpu': 2, 'memory': 512, 'disks': [], 'netcards': []}
            extensions: dict with specific attributes depending on guest type

        Returns:
            None

        Raises:
            None
        """
        raise NotImplementedError()
    # hotplug()

    def installPackages(self, packages):
        """
        Use the system's package management facilities and install the
        specified packages.

        Args:
            packages: list of package names to install

        Returns:
            None

        Raises:
            RuntimeError: if action failed
        """
        # delegate to the distro specific object which knows better how to
        # handle package management
        self._distroObj.installPackages(self._sshConn, packages)
    # installPackages()

    def login(self, timeout=60):
        """
        Execute the login to the guest system using the credentials
        provided.

        Args:
            timeout: how many seconds to wait for connection

        Returns:
            None

        Raises:
            ConnectionError: if protocol or network error occurred
            PermissionError: if login failed because credentials are invalid
        """
        # create a ssh connection using our ssh module
        sshConn = SshClient()
        sshConn.login(self.host_name, user=self.user, passwd=self.passwd,
                      timeout=timeout)
        self._sshConn = sshConn

        # find a suitable distro class for this environment
        shellObj = self._sshConn.openShell()
        found = None
        for module in DISTRO_MODULES:
            # generic class: use it as last option
            if module is genericModule:
                continue

            # dristro class match environment: use it
            if module.distroClass.detect(shellObj):
                found = module.distroClass
                break

        # no distro class matches this environment: fallback to generic class
        if not found:
            # not a linux kernel: cannot continue
            if not genericModule.distroClass.detect(shellObj):
                raise ConnectionError('Target system is not Linux')
            found = genericModule.distroClass

        # instantiate the distro object
        self._loggerObj.debug(
            "create distro system_name='%s' distro_obj='%s'",
            self.name,
            found.__name__
        )
        self._distroObj = found(self._sshConn)
    # login()

    def logoff(self):
        """
        Close an active connection to the guest system

        Args:
            None

        Returns:
            None

        Raises:
            None
        """
        self._loggerObj.debug("logoff system_name='%s'", self.name)

        # remove reference to distro object so that its destructor is called
        self._distroObj = None
        # close ssh connection
        self._sshConn.logoff()
    # logoff()

    def openSession(self, extensions=None):
        """
        Returns a expect-like object which can be used for sending commands and
        receiving output from a guest's shell.

        Args:
            extensions: dictionary with parameters, not used currently

        Returns:
            instance of GuestSessionLinux

        Raises:
            None
        """
        return GuestSessionLinux(self._sshConn.openShell())
    # openSession()

    def pullFile(self):
        """
        TODO
        """
        raise NotImplementedError()
    # pullFile()

    def pushFile(self):
        """
        TODO
        """
        raise NotImplementedError()
    # pushFile()

    def stop(self):
        """
        Stop a given guest by executing a shutdown command

        Args:
            None

        Returns:
            None

        Raises:
            None
        """
        shellObj = self._sshConn.openShell()
        shellObj.run('nohup halt &')
    # stop()

# GuestLinux
