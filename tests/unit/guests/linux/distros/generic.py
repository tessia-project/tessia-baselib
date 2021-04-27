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
Unit test for linux.distros.generic module
"""

#
# IMPORTS
#
from tessia.baselib.guests.linux.distros.generic import DistroGeneric
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

    def _check_install_pkg(self):
        """
        Auxiliary function to validate the installPackages() method by using
        object variables previously set by the caller function depending on the
        package manager type (apt-get, yum, zypper, etc.) to be tested.

        Args:
            None

        Raises:
            AssertionError: if any verification fails
        """
        # make the shell mock return a mock function representing its run()
        # method. This mock run() will return package manager output depending
        # on the type set by some variables set in the object like
        # self._pkg_manager
        mock_ssh_shell = Mock(name='SshShell', spec_set=['close', 'run'])
        mock_ssh_shell.run.side_effect = self._mock_run

        # create a SshClient mock object to return the SshShell mock on
        # open_shell() call
        mock_ssh_client = Mock(name='SshClient', spec_set=['open_shell'])
        mock_ssh_client.open_shell.return_value = mock_ssh_shell

        # create our distro object for testing
        distro_obj = DistroGeneric(mock_ssh_client)

        # check behavior when asking to install valid package
        self.assertIs(None, distro_obj.install_packages(['python3']))
        mock_ssh_shell.run.assert_any_call(self._which_cmd)
        mock_ssh_shell.run.assert_called_with(
            '{} python3'.format(self._install_cmd)
        )

        # check behavior when asking to install an already installed package
        mock_ssh_shell.reset_mock()
        self.assertIs(
            None, distro_obj.install_packages(['already_installed_pkg']))
        # check if caching worked and no further 'which' commands were
        # performed
        try:
            mock_ssh_shell.run.assert_any_call(self._which_cmd)
        # raise exception means it was not called, which is what we want
        except AssertionError:
            pass
        else:
            raise AssertionError("'which' was called by install_packages")
        # check if correct install command was issued
        mock_ssh_shell.run.assert_called_with(
            '{} already_installed_pkg'.format(self._install_cmd)
        )

        # check if it fails when asking to install an invalid package and if
        # it properly concatenates multiple packages
        mock_ssh_shell.reset_mock()
        self.assertRaisesRegex(
            RuntimeError,
            r'^Failed to install package\(s\): .*',
            distro_obj.install_packages,
            ['invalid_pkg', 'another_invalid_pkg']
        )
        # check if caching worked and no further 'which' commands were
        # performed
        try:
            mock_ssh_shell.run.assert_any_call(self._which_cmd)
        # raise exception means it was not called, which is what we want
        except AssertionError:
            pass
        else:
            raise AssertionError("'which' was called by install_packages")
        # check correct install command line with package names concatenated
        mock_ssh_shell.run.assert_called_with(
            '{} invalid_pkg another_invalid_pkg'.format(self._install_cmd)
        )

    # _check_install_pkg()

    def _mock_run(self, cmd):
        """
        A mock function to replace SshShell.run during the tests related to
        installPackages() method. Since the package manager type being tested
        cannot be passed via method prototype (as it has to mimic run method's
        behavior) we set them as object variables so that it knows for which
        package manager type to generate output.

        Args:
            cmd (str): command to execute received from the distro class

        Returns:
            tuple: (exit_code, output) depending on the scenario being tested

        Raises:
            IOError: if output txt file cannot be read
        """
        # which command performed: return the expected which output
        if cmd == self._which_cmd:
            return (0, self._which_ret)

        # package install command performed: retrieve output from txt file
        if cmd.startswith(self._install_cmd):

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
            with open(
                '{}/{}/{}'.format(my_dir, self._pkg_manager, file_name),
                'r') as file_obj:
                resp_output = file_obj.read()

            return (exit_code, resp_output)

        # if none of the above, return an error condition output
        return (1, 'invalid command')
    # _mock_run()

    def test_install_pkg_aptget(self):
        """
        Verify if installPackages correctly works for an apt-get based system

        Args:
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
        self._check_install_pkg()
    # test_install_pkg_aptget()

    def test_install_pkg_yum(self):
        """
        Verify if installPackages correctly works for a yum based system

        Args:
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
        self._check_install_pkg()
    # test_install_pkg_yum()

    def test_install_pkg_zypper(self):
        """
        Verify if installPackages correctly works for a zypper based system

        Args:
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
        self._check_install_pkg()
    # test_install_pkg_zypper()

    def test_detect_system(self):
        """
        Verify if the detection routine works correctly

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # make the mock for SshShell to return a valid response to uname -a
        mock_ssh_shell = Mock(name='SshShell', spec_set=['run'])
        mock_ssh_shell.run.return_value = (
            0,
            'Linux dummy 4.4.6-200.x86_64 #1 SMP Wed Mar 16 22:13:40 UTC 2016 '
            'x86_64 x86_64 x86_64 GNU/Linux'
        )
        # validate detect for a valid system
        self.assertIs(True, DistroGeneric.detect(mock_ssh_shell))
        mock_ssh_shell.run.assert_called_with('uname -a')

        # make shell return a successful output but for a non linux kernel
        mock_ssh_shell.reset_mock()
        mock_ssh_shell.run.return_value = (
            0,
            'OtherOS dummy 4.4.6-200.x86_64 #1 SMP Wed Mar 16 22:13:40 '
            'UTC 2016 x86_64 x86_64 x86_64 Other/OS'
        )
        # validate detect does not accept a non linux kernel
        self.assertIs(False, DistroGeneric.detect(mock_ssh_shell))
        mock_ssh_shell.run.assert_called_with('uname -a')

        # make shell return that command failed
        mock_ssh_shell.reset_mock()
        mock_ssh_shell.run.return_value = (1, 'command not found')
        # validate detect fails when command failed
        self.assertIs(False, DistroGeneric.detect(mock_ssh_shell))
        mock_ssh_shell.run.assert_called_with('uname -a')

        # make shell return an unexpected output
        mock_ssh_shell.reset_mock()
        mock_ssh_shell.run.return_value = (0, 'unexpected')
        # validate detect
        self.assertIs(False, DistroGeneric.detect(mock_ssh_shell))
        mock_ssh_shell.run.assert_called_with('uname -a')

        # make shell return an empty output
        mock_ssh_shell.reset_mock()
        mock_ssh_shell.run.return_value = (0, '')
        # validate detect
        self.assertIs(False, DistroGeneric.detect(mock_ssh_shell))
        mock_ssh_shell.run.assert_called_with('uname -a')
    # test_detect_system()

# TestDistroGeneric
