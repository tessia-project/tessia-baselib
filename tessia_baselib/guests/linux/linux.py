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
from tessia_baselib.guests.linux.storage.pool import StoragePool

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
        self.__ssh_conn = None

        # distro class to use, will be determined by login()
        self.__distro_obj = None

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

    @property
    def _distro_obj(self):
        """
        Provide access to distro object
        """
        if self.__distro_obj is None:
            raise RuntimeError("You need to login first")
        return self.__distro_obj
    # _distro_obj()

    @property
    def ssh_conn(self):
        """
        Provide access to ssh connection object
        """
        if self.__ssh_conn is None:
            raise RuntimeError("You need to login first")
        return self.__ssh_conn
    # ssh_conn()

    def hotplug(self, cpu=None, memory=None, vols=None, extensions=None):
        """
        Performs a logical hotplug of resources in the guest operating system.

        Args:
            cpu (int): number of new cpus to activate
            memory (int): MiB of memory to activate, on Linux it has to be a
                          multiple of a section unit which size is is
                          architecture dependent
            vols (list): list of volumes to activate
            extensions (dict): not used

        Raises:
            NotImplementedError: if cpu or memory hotplug is attempted
            RuntimeError: in case user has not logged in first

        Returns:
            dict: contains information on the operation result, in the form:
                  {
                  # disks activated with their device paths
                  'vols': {'volume_id1': '/dev/device_path1'}
                  }
        """
        result = {}
        if cpu:
            raise NotImplementedError('cpu hotplug not supported yet')
        if memory:
            raise NotImplementedError('memory hotplug not supported yet')

        # TODO: validate vols dict against a schema
        if vols:
            pool = StoragePool(vols, self.ssh_conn)
            resp = pool.activate()
            result['vols'] = resp

        return result
    # hotplug()

    def install_packages(self, packages):
        """
        Use the system's package management facilities and install the
        specified packages.

        Args:
            packages (list): package names to install

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

        Raises:
            ConnectionError: if protocol or network error occurred
            PermissionError: if login failed because credentials are invalid
        """
        # create a ssh connection using our ssh module
        ssh_conn = SshClient()
        ssh_conn.login(self.host_name, user=self.user, passwd=self.passwd,
                       timeout=timeout)
        self.__ssh_conn = ssh_conn

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
        self.__distro_obj = found(self.ssh_conn)
    # login()

    def logoff(self):
        """
        Close an active connection to the guest system

        Args:
            None

        Raises:
            None
        """
        self._logger.debug("logoff system_name='%s'", self.name)

        # remove reference to distro object so that its destructor is called
        self.__distro_obj = None
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
            RuntimeError: in case user has not logged in first
        """
        return GuestSessionLinux(self.ssh_conn.open_shell())
    # open_session()

    def pull_file(self):
        """
        TODO
        """
        raise NotImplementedError()
    # pull_file()

    def push_file(self, source_url, target_path, write_mode='wb'):
        """
        Retrieve a file from source_url and copy it to a file on this
        ssh host.
        See base class for details.

        Raises:
            RuntimeError: in case user has not logged in first
        """
        self.ssh_conn.push_file(source_url, target_path, write_mode)
    # push_file()

    def stop(self):
        """
        Stop a given guest by executing a shutdown command

        Args:
            None

        Raises:
            RuntimeError: in case user has not logged in first
        """
        shell_obj = self.ssh_conn.open_shell()
        shell_obj.run('nohup halt &')
    # stop()
# GuestLinux
