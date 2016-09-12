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
Implementation of guest interface for Linux
"""

#
# IMPORTS
#
from tessia_baselib.common.logger import get_logger
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
            system_name (str): guest name
            host_name (str): hostname or ip address of system
            user (str): user to login to system
            passwd (str): password to login to system
            extensions (dict): values specific to each guest type

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
        self._logger = get_logger(__name__)

        # ssh connection to be initialized by login()
        self.ssh_conn = None

        # distro class to use, will be determined by login()
        self._distro_obj = None

        # log object creation for debugging
        self._logger.debug(
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
            method (str): attach (hotplug) or detach (hotunplug)
            resources (dict): in the form:
                       {'cpu': 2, 'memory': 512, 'disks': [], 'netcards': []}
            extensions (dict): specific attributes depending on guest type

        Returns:
            None

        Raises:
            NotImplementedError: TODO
        """
        raise NotImplementedError()
    # hotplug()

    def install_packages(self, packages):
        """
        Use the system's package management facilities and install the
        specified packages.

        Args:
            packages (list): package names to install

        Returns:
            None

        Raises:
            RuntimeError: if action failed
        """
        # delegate to the distro specific object which knows better how to
        # handle package management
        self._distro_obj.install_packages(self.ssh_conn, packages)
    # install_packages()

    def login(self, timeout=60):
        """
        Execute the login to the guest system using the credentials
        provided.

        Args:
            timeout (int): how many seconds to wait for connection

        Returns:
            None

        Raises:
            ConnectionError: if protocol or network error occurred
            PermissionError: if login failed because credentials are invalid
        """
        # create a ssh connection using our ssh module
        ssh_conn = SshClient()
        ssh_conn.login(self.host_name, user=self.user, passwd=self.passwd,
                       timeout=timeout)
        self.ssh_conn = ssh_conn

        # find a suitable distro class for this environment
        shell_obj = self.ssh_conn.open_shell()
        found = None
        for module in DISTRO_MODULES:
            # generic class: use it as last option
            if module is genericModule:
                continue

            # dristro class match environment: use it
            if module.Distro.detect(shell_obj):
                found = module.Distro
                break

        # no distro class matches this environment: fallback to generic class
        if not found:
            # not a linux kernel: cannot continue
            if not genericModule.Distro.detect(shell_obj):
                raise ConnectionError('Target system is not Linux')
            found = genericModule.Distro

        # instantiate the distro object
        self._logger.debug(
            "create distro system_name='%s' _distro_obj='%s'",
            self.name,
            found.__name__
        )
        self._distro_obj = found(self.ssh_conn)
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
        self._logger.debug("logoff system_name='%s'", self.name)

        # remove reference to distro object so that its destructor is called
        self._distro_obj = None
        # close ssh connection
        self.ssh_conn.logoff()
    # logoff()

    def open_session(self, extensions=None):
        """
        Returns a expect-like object which can be used for sending commands and
        receiving output from a guest's shell.

        Args:
            extensions (dict): parameters, not used currently

        Returns:
            GuestSessionLinux: object

        Raises:
            None
        """
        return GuestSessionLinux(self.ssh_conn.open_shell())
    # open_session()

    def pull_file(self):
        """
        TODO
        """
        raise NotImplementedError()
    # pull_file()

    def push_file(self, source_url, target_file_path, write_mode='wb'):
        """
        Retrieve a file from source_url and copy it to a file on this
        ssh host.

        Args:
            source_url (str): Url to which the source file should be copied.
                        The following schemes are accepted:
                        ssh://[user[:pass]]@ssh_host[:port]/target/path
                        file:///target/path
                        http, https or ftp urls

                        A ssh url refers to a file on another ssh host.
                        A file url refers to a file on the local host,
                        and any host portion of the url is ignored.

                        The url has to be properly quoted.
                        See urllib.parse.quote. Don't forget to call it with
                        safe='/' when quoting paths and safe='' when quoting
                        other components (e.g. the password, which could
                        contain a '/' which must be quoted).

            target_file_path (str): Path of the file in this ssh host to which
                                    the source will be copied.
            write_mode (str): Either 'wb' or 'ab', for truncating and appending
                               to the target file, respectively.

        Returns:
            None

        Raises:
            None
        """
        if self.ssh_conn is None:
            self._logger.warning("Not connected to the linux host")
            return

        self.ssh_conn.push_file(source_url, target_file_path, write_mode)
    # push_file()

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
        shell_obj = self.ssh_conn.open_shell()
        shell_obj.run('nohup halt &')
    # stop()

# GuestLinux
