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
Defines the interface for guest classes
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

class GuestBase(metaclass=abc.ABCMeta):
    """
    This is the abstract Guest class which defines the interface to be
    implemented by each guest driver
    """

    # the identifier for this guest class, should be a lowercase string
    GUEST_ID = 'base'

    def __init__(self, system_name, host_name, user, passwd, extensions):
        """
        Constructor.

        Args:
            system_name (str): the guest name
            host_name (str): hostname or ip address of system
            user (str): user to login to system
            passwd (str): password to login to system
            extensions (dict): a dictionary containing values specific to each
                               guest type

        Raises:
            None
        """
        # store instance values
        self.name = system_name
        self.host_name = host_name
        self.user = user
        self.passwd = passwd
        self.extensions = extensions

    # __init__()

    @abc.abstractmethod
    def hotplug(self, cpu=None, memory=None, vols=None, extensions=None):
        """
        Performs a logical hotplug of resources in the guest operating system.
        Concrete classes should return a dict with operation result whose
        format is guest type dependant.

        Args:
            cpu (int): number of new cpus to activate
            memory (int): MiB of memory to activate, it might need to be a
                          multiple of certain value depending on the OS type
            vols (list): list of volumes to activate
            extensions (dict): not used

        Raises:
            NotImplementedError: as it has to be implemented by child class
        """
        raise NotImplementedError()
    # hotplug()

    @abc.abstractmethod
    def login(self, timeout=60):
        """
        Execute the login to the guest system using the credentials
        provided.

        Args:
            timeout (int): how many seconds to wait for connection

        Raises:
            NotImplementedError: as it has to be implemented by child class
        """
        raise NotImplementedError()
    # login()

    @abc.abstractmethod
    def logoff(self):
        """
        Close an active connection to the guest system

        Args:
            None

        Raises:
            NotImplementedError: as it has to be implemented by child class
        """
        raise NotImplementedError()
    # logoff()

    @abc.abstractmethod
    def install_packages(self, packages):
        """
        Use the system's package management facilities and install the
        specified packages.

        Args:
            packages (list): package names to install

        Raises:
            NotImplementedError: as it has to be implemented by child class
        """
        raise NotImplementedError()
    # install_packages()

    @abc.abstractmethod
    def open_session(self, extensions=None):
        """
        Returns a expect-like object which can be used for sending commands and
        receiving output from a guest's shell. Concrete implementations should
        return an instance of GuestSession.

        Args:
            extensions (dict): params specific to each guest type

        Raises:
            NotImplementedError: as it has to be implemented by child class
        """
        raise NotImplementedError()
    # open_session()

    @abc.abstractmethod
    def pull_file(self):
        """
        TODO
        """
        raise NotImplementedError()
    # pull_file()

    @abc.abstractmethod
    def push_file(self, source_url, target_path, write_mode='wb'):
        """
        Retrieve a file from source_url and copy it to a file on this
        ssh host. In concrete classes should raise RuntimeError in case of
        errors.

        Args:
            source_url (str): url where the source file should be copied from.
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

            target_path (str): target filepath in this ssh host
            write_mode (str): Either 'wb' or 'ab', for truncating and appending
                               to the target file, respectively.

        Raises:
            NotImplementedError: in case this method is called, since it is
                                 implemented in the child class.
        """
        raise NotImplementedError()
    # push_file()

    @abc.abstractmethod
    def stop(self):
        """
        Stop a given guest by executing a shutdown command

        Args:
            None

        Raises:
            NotImplementedError: as it has to be implemented by child class
        """
        raise NotImplementedError()
    # stop()

# GuestBase
