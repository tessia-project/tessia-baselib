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

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

class DistroGeneric(object):
    """
    This class implements support for actions on a generic Linux environment
    """

    # mapping of package managers we support and their pkg installation
    # commands. For now we simply deal with each package manager in the
    # generic class but as the content grows it should be splitted into the
    # specific distro classes
    PKG_MANAGERS = {
        'apt-get': 'apt-get install -yq --no-install-recommends',
        'yum': 'yum -q -y install',
        'zypper': 'zypper -q -n install',
    }

    def __init__(self, sshConn):
        """
        Constructor, initializes logger object and stores reference to ssh
        connection object.

        Args:
            sshConn: instance of SshClient

        Returns:
            None

        Raises:
            None
        """
        # initialize logger object
        self._loggerObj = getLogger(__name__)

        # ssh connection object
        self._sshConn = sshConn

        # package manager type, it will be detected the first time
        # installPackages() is executed
        self._pkg_manager = None
    # __init__()

    @classmethod
    def detect(cls, shellObj):
        """
        Verify if the environment where the provided shell is running is a
        Linux system. Since this class is generic we basically only confirm
        that the kernel is named Linux.
        This method is defined in the class so that it can be used to determine
        a target system type before instantiating the appropriate object to be
        used.

        Args:
            shellObj: shell object providing a method to execute command and
                      receive output back.

        Returns:
            True if system is running a Linux kernel, False otherwise

        Raises:
            whatever the shell object raises
        """
        # confirm the kernel is named 'Linux'
        _, output = shellObj.run('uname -a')
        if len(output) > 0 and output.split()[0].lower() == 'linux':
            return True

        return False
    # detect()

    def installPackages(self, package_list):
        """
        Use the system's package management facilities and install the
        specified packages.

        Args:
            sshConn: instance of SshClient
            package_list: list of package names to install

        Returns:
            None

        Raises:
            RuntimeError: if installation fails or no supported pkg manager is
                          available
        """
        # get a shell to perform commands
        shellObj = self._sshConn.openShell()

        # package manager not detected yet: do it
        if self._pkg_manager is None:
            for pkg_manager in self.PKG_MANAGERS.keys():
                ret, output = shellObj.run('which {}'.format(pkg_manager))
                if ret == 0:
                    self._pkg_manager = pkg_manager
                    break
            if self._pkg_manager is None:
                raise RuntimeError('No supported package manager found')
        install_cmd = self.PKG_MANAGERS[self._pkg_manager]
        self._loggerObj.debug("install_cmd='%s'", install_cmd)

        # as an improvement, we could consider accepting a 'description list'
        # which has the mapping between package names and distros to make it
        # easier for a tester to only mantain this list and not having to deal
        # with checking distro to pass correct package name to this method.
        ret, output = shellObj.run(
            '{} {}'.format(install_cmd, ' '.join(package_list)))
        if ret != 0:
            raise RuntimeError(
                'Failed to install package(s): {}'.format(output)
            )

        shellObj.close()

    # installPackages()

# DistroGeneric

distroClass = DistroGeneric
