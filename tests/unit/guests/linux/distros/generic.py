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
from tessia_baselib.common.ssh.exceptions import SshShellError
from tessia_baselib.guests.linux.distros.generic import DistroGeneric
from unittest import TestCase
from unittest.mock import Mock

import os

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

class TestDistroGeneric(TestCase):
    """
    Unit test for the DistroGeneric class
    """
    def __init__(self, *args, **kwargs):
        """
        Constructor, declares internal variables to be used later by test
        methods

        Args:
            args: any positional arguments which to be forwarded to parent
                  constructor
            kwargs: any keyword arguments which to be forwarded to parent
                    constructor

        Returns:
            None

        Raises:
            None
        """
        super().__init__(*args, **kwargs)

        # variables below used when testing installPackages() method, these
        # are set by each testInstallPkg* method depending on the package
        # manager type

        # package manager type (apt-get, yum, zypper)
        self._pkg_manager = None
        # command used by Distro class to discover package manager type
        self._which_cmd = None
        # output from which command
        self._which_ret = None
        # the command line used for the package manager to install packages
        self._install_cmd = None
    # __init__()

    def _checkInstallPkg(self):
        """
        Auxiliary function to validate the installPackages() method by using
        object variables previously set by the caller function depending on the
        package manager type (apt-get, yum, zypper, etc.) to be tested.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if any verification fails
        """
        # make the shell mock return a mock function representing its run()
        # method. This mock run() will return package manager output depending
        # on the type set by some variables set in the object like
        # self._pkg_manager
        mockSshShell = Mock(name='SshShell', spec_set=['close', 'run'])
        mockSshShell.run.side_effect = self._mockRun

        # create a SshClient mock object to return the SshShell mock on
        # openShell() call
        mockSshClient = Mock(name='SshClient', spec_set=['openShell'])
        mockSshClient.openShell.return_value = mockSshShell

        # create our distro object for testing
        distroObj = DistroGeneric(mockSshClient)

        # check behavior when asking to install valid package
        self.assertIs(None, distroObj.installPackages(['python3']))
        mockSshShell.run.assert_any_call(self._which_cmd)
        mockSshShell.run.assert_called_with(
            '{} python3'.format(self._install_cmd)
        )

        # check behavior when asking to install an already installed package
        mockSshShell.reset_mock()
        self.assertIs(None, distroObj.installPackages(['already_installed_pkg']))
        # check if caching worked and no further 'which' commands were
        # performed
        mockSshShell.run.assert_not_called(self._which_cmd)
        # check if correct install command was issued
        mockSshShell.run.assert_called_with(
            '{} already_installed_pkg'.format(self._install_cmd)
        )

        # check if it fails when asking to install an invalid package and if
        # it properly concatenates multiple packages
        mockSshShell.reset_mock()
        self.assertRaisesRegex(
            RuntimeError,
            '^Failed to install package\(s\): .*',
            distroObj.installPackages,
            ['invalid_pkg', 'another_invalid_pkg']
        )
        # check if caching worked and no further 'which' commands were
        # performed
        mockSshShell.run.assert_not_called(self._which_cmd)
        # check correct install command line with package names concatenated
        mockSshShell.run.assert_called_with(
            '{} invalid_pkg another_invalid_pkg'.format(self._install_cmd)
        )

    # _checkInstallPkg()

    def _mockRun(self, cmd):
        """
        A mock function to replace SshShell.run during the tests related to
        installPackages() method. Since the package manager type being tested
        cannot be passed via method prototype (as it has to mimic run method's
        behavior) we set them as object variables so that it knows for which
        package manager type to generate output.

        Args:
            cmd: the command to execute received from the distro class

        Returns:
            tuple (exit_code, output) depending on the scenario being tested

        Raises:
            IOError: if output txt file cannot be read
        """
        # which command performed: return the expected which output
        if cmd == self._which_cmd:
            return (0, self._which_ret)

        # package install command performed: retrieve output from txt file
        elif cmd.startswith(self._install_cmd):

            # command to test invalid package: retrieve from error output and
            # set status code to error
            if cmd.find(' invalid_pkg') > 0:
                file_name = 'error.txt'
                exit_code = 1

            # command to test already installed package: retrieve appropriate
            # output and set status code to success
            elif cmd.find(' already_installed_pkg') > 0:
                file_name = 'installed.txt'
                exit_code = 0

            # command to test normal installation: retrieve appropriate
            # output and  set status code to success
            else:
                file_name = 'success.txt'
                exit_code = 0

            # read the content from txt file under folder named after package
            # manager type in directory where this file is located
            my_dir = os.path.dirname(os.path.abspath(__file__))
            fileObj = open(
                '{}/{}/{}'.format(my_dir, self._pkg_manager, file_name),
                'r'
            )
            resp_output = fileObj.read()
            fileObj.close()

            return (exit_code, resp_output)

        # if none of the above, return an error condition output
        return (1, 'invalid command')
    # _mockRun()

    def testInstallPkgAptget(self):
        """
        Verify if installPackages correctly works for an apt-get based system

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # package manager type
        self._pkg_manager = 'apt-get'
        # command used by Distro class to discover package manager type
        self._which_cmd = 'which apt-get'
        # output from which command
        self._which_ret = '/usr/bin/apt-get'
        # the command line used for the package manager to install packages
        self._install_cmd = 'apt-get install -yq --no-install-recommends'

        # call auxiliary function to perform verification
        self._checkInstallPkg()
    # testInstallPkgAptget()

    def testInstallPkgYum(self):
        """
        Verify if installPackages correctly works for a yum based system

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # package manager type
        self._pkg_manager = 'yum'
        # command used by Distro class to discover package manager type
        self._which_cmd = 'which yum'
        # output from which command
        self._which_ret = '/usr/bin/yum'
        # the command line used for the package manager to install packages
        self._install_cmd = 'yum -q -y install'

        # call auxiliary function to perform verification
        self._checkInstallPkg()
    # testInstallPkgYum()

    def testInstallPkgZypper(self):
        """
        Verify if installPackages correctly works for a zypper based system

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # package manager type
        self._pkg_manager = 'zypper'
        # command used by Distro class to discover package manager type
        self._which_cmd = 'which zypper'
        # output from which command
        self._which_ret = '/usr/bin/zypper'
        # the command line used for the package manager to install packages
        self._install_cmd = 'zypper -q -n install'

        # call auxiliary function to perform verification
        self._checkInstallPkg()
    # testInstallPkgZypper()

    def testDetectSystem(self):
        """
        Verify if the detection routine works correctly

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # make the mock for SshShell to return a valid response to uname -a
        mockSshShell = Mock(name='SshShell', spec_set=['run'])
        mockSshShell.run.return_value = (
            0,
            'Linux dummy 4.4.6-200.x86_64 #1 SMP Wed Mar 16 22:13:40 UTC 2016 '
            'x86_64 x86_64 x86_64 GNU/Linux'
        )
        # validate detect for a valid system
        self.assertIs(True, DistroGeneric.detect(mockSshShell))
        mockSshShell.run.assert_called_with('uname -a')

        # make shell return a successful output but for a non linux kernel
        mockSshShell.reset_mock()
        mockSshShell.run.return_value = (
            0,
            'OtherOS dummy 4.4.6-200.x86_64 #1 SMP Wed Mar 16 22:13:40 UTC 2016 '
            'x86_64 x86_64 x86_64 Other/OS'
        )
        # validate detect does not accept a non linux kernel
        self.assertIs(False, DistroGeneric.detect(mockSshShell))
        mockSshShell.run.assert_called_with('uname -a')

        # make shell return that command failed
        mockSshShell.reset_mock()
        mockSshShell.run.return_value = (1, 'command not found')
        # validate detect fails when command failed
        self.assertIs(False, DistroGeneric.detect(mockSshShell))
        mockSshShell.run.assert_called_with('uname -a')

        # make shell return an unexpected output
        mockSshShell.reset_mock()
        mockSshShell.run.return_value = (0, 'unexpected')
        # validate detect
        self.assertIs(False, DistroGeneric.detect(mockSshShell))
        mockSshShell.run.assert_called_with('uname -a')

        # make shell return an empty output
        mockSshShell.reset_mock()
        mockSshShell.run.return_value = (0, '')
        # validate detect
        self.assertIs(False, DistroGeneric.detect(mockSshShell))
        mockSshShell.run.assert_called_with('uname -a')

# TestDistroGeneric
