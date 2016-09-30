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
Unit test for linux module
"""

#
# IMPORTS
#
from tessia_baselib.guests.linux.linux import GuestLinux
from tempfile import NamedTemporaryFile
from unittest import TestCase
from unittest.mock import Mock
from unittest.mock import patch

import logging

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

class TestGuestLinux(TestCase):
    """
    Unit test for the GuestLinux class
    """
    def _check_init(self):
        """
        Check if the class constructor works as expected and return the object
        for further testing.

        Args:
            None

        Returns:
            GuestLinux: object

        Raises:
            AssertionError: if validation fails
        """
        # instantiate the guest class we want to test
        system_name = 'dummy_system'
        host_name = 'dummy.domain.com'
        user = 'root'
        passwd = 'somepwd'
        extensions = {}
        guest_obj = GuestLinux(
            system_name, host_name, user, passwd, extensions)

        # validate if attributes were correctly assigned to object
        self.assertEqual('linux', guest_obj.GUEST_ID)
        self.assertIs(system_name, guest_obj.name)
        self.assertIs(host_name, guest_obj.host_name)
        self.assertIs(user, guest_obj.user)
        self.assertIs(passwd, guest_obj.passwd)
        self.assertIs(extensions, guest_obj.extensions)

        # return object for further testing
        return guest_obj
    # _check_init()

    def _check_login(self, guest_obj, mock_ssh_client_cls, mock_ssh_client,
                     mock_ssh_shell, distro_name, distro_cmd):
        """
        Check if the login() method works as expected

        Args:
            guest_obj (GuestLinux): instance of GuestLinux
            mock_ssh_client_cls (Mock): the mock created for class SshClient
            mock_ssh_client (Mock): the mock created for object of SshClient
            mock_ssh_shell (Mock): the mock created for object of SshShell
            distro_name (str): name of distro class that should be created
            distro_cmd (str): expected command used to identify environment

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        # perform login to exercise distro detection
        guest_obj.login()

        # validate if instantiating SshClient was correct
        mock_ssh_client_cls.assert_called_with()

        # validate usage of SshClient object was correct
        mock_ssh_client.login.assert_called_with(
            guest_obj.host_name,
            user=guest_obj.user,
            passwd=guest_obj.passwd,
            timeout=60
        )
        mock_ssh_client.open_shell.assert_called_with()

        # validate if the right distro object was created
        self.assertIs(distro_name, guest_obj._distro_obj.__class__.__name__)

        # validate the right command was issued for env detection
        mock_ssh_shell.run.assert_called_with(distro_cmd)

    # _check_login()

    def _check_logoff(self, guest_obj, mock_ssh_client):
        """
        Check if the logoff() method works as expected

        Args:
            guest_obj (GuestLinux): object
            mock_ssh_client (Mock): the mock created for object of SshClient

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        # call method and verify if it correctly drops distro object and
        # closes ssh connection
        guest_obj.logoff()
        self.assertIs(None, guest_obj._distro_obj)
        mock_ssh_client.logoff.assert_called_with()
    # _check_logoff()

    def _check_open_session(self, guest_obj):
        """
        Check if the open_session() method works as expected

        Args:
            guest_obj (GuestLinux): object

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        session = guest_obj.open_session()
        self.assertIs('GuestSessionLinux', session.__class__.__name__)
    # _check_open_session()

    @staticmethod
    def _check_stop(guest_obj, mock_ssh_shell, stop_cmd):
        """
        Check if the stop() method works as expected

        Args:
            guest_obj (GuestLinux): object
            mock_ssh_shell (Mock): representation for object of SshShell
            stop_cmd (str): expected command used to shutdown system

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        # call method and verify if it executed cmd in ssh shell
        guest_obj.stop()
        mock_ssh_shell.run.assert_called_with(stop_cmd)
    # _check_stop()

    # mock the ssh module to pretend we connect to a real system
    @patch('tessia_baselib.guests.linux.linux.SshClient', spec_set=True)
    def test_normal_flow_generic_distro(self, mock_ssh_client_cls):
        """
        Exercise a normal flow for a generic linux guest.

        Args:
            mock_ssh_client_cls (Mock): representation of SshClient class

        Returns:
            None

        Raises:
            AssertionError: if the guest object does not behave as expected
        """
        # set a simple log configuration to catch messages from all levels
        # and output to a file which we will check later
        log_file = NamedTemporaryFile()
        logging.basicConfig(filename=log_file.name, filemode='w',
                            level=logging.DEBUG)

        # define the mock for SshShell containing only the run method which
        # returns a successful exit code and the response below to a
        # 'uname -a' cmd
        mock_ssh_shell = Mock(name='SshShell', spec_set=['run'])
        mock_ssh_shell.run.return_value = (
            0,
            'Linux dummy 4.4.6-200.x86_64 #1 SMP Wed Mar 16 22:13:40 UTC 2016 '
            'x86_64 x86_64 x86_64 GNU/Linux'
        )

        # define a SshClient object which will return the SshShell mock created
        # in previous step
        mock_ssh_client = Mock(
            name='SshClient', spec_set=['login', 'logoff', 'open_shell']
        )
        mock_ssh_client.open_shell.return_value = mock_ssh_shell

        # make the mock SshClientClass from patch decorator return the object
        # we just defined upon instantiation
        mock_ssh_client_cls.return_value = mock_ssh_client

        # validate the constructor of the guest class
        guest_obj = self._check_init()

        # validate login() method
        self._check_login(
            guest_obj, mock_ssh_client_cls, mock_ssh_client, mock_ssh_shell,
            'DistroGeneric', 'uname -a'
        )

        # validate open_session() method
        self._check_open_session(guest_obj)

        # validate stop() method
        self._check_stop(guest_obj, mock_ssh_shell, 'nohup halt &')

        # validate logoff() method
        self._check_logoff(guest_obj, mock_ssh_client)

        # validate the logging was correct
        # define the content we expect to see in the log file
        log_prefix = 'DEBUG:tessia_baselib.guests.linux.linux'
        expected_log = (
            "{0}:create GuestLinux: name='{1.name}' host_name='{1.host_name}' "
            "user='{1.user}' extensions='{1.extensions}'\n".format(
                log_prefix, guest_obj)
        )
        expected_log += (
            "{}:create distro system_name='{}' _distro_obj='DistroGeneric'\n"
            .format(log_prefix, guest_obj.name)
        )
        expected_log += (
            "{}:logoff system_name='{}'\n".format(log_prefix, guest_obj.name)
        )
        # retrieve the content written in the log file
        log_fd = open(log_file.name, 'r')
        actual_log = log_fd.read()
        log_fd.close()
        # allow unittest class to show the full diff in case of error
        # pylint: disable=invalid-name
        self.maxDiff = None
        # perform the comparison to validate the content
        self.assertEqual(expected_log, actual_log)

    # test_normal_flow_generic_distro()

    # mock the ssh module to pretend we connect to a real system
    @patch('tessia_baselib.guests.linux.linux.SshClient', spec_set=True)
    def test_fail_flow_invalid_distro(self, mock_ssh_client_cls):
        """
        Simulate the connection to a system which does not claim to have a
        Linux kernel.

        Args:
            mock_ssh_client_cls (Mock): represents the SshClient class

        Returns:
            None

        Raises:
            AssertionError: if guest object does not raise NotImplementedError
                            for the called methods
        """
        # define the mock for SshShell with only the run method which fails to
        # execute commands
        mock_ssh_shell = Mock(name='SshShell', spec_set=['run'])
        mock_ssh_shell.run.return_value = (1, 'command not found')

        # SshClient instance which will return the SshShell mock we just
        # defined
        mock_ssh_client = Mock(
            name='SshClient', spec_set=['login', 'open_shell'])
        mock_ssh_client.open_shell.return_value = mock_ssh_shell

        # make the mock SshClientClass from patch decorator return the object
        # we just defined upon instantiation
        mock_ssh_client_cls.return_value = mock_ssh_client

        # instantiate the guest class we want to test
        system_name = 'dummy_system'
        host_name = 'dummy.domain.com'
        user = 'root'
        passwd = 'somepwd'
        extensions = {}
        guest_obj = GuestLinux(
            system_name, host_name, user, passwd, extensions)

        # check if correctly raises the exception
        self.assertRaises(ConnectionError, guest_obj.login)

        # change the mock now to successfully execute the command but report an
        # incorrect kernel name
        mock_ssh_shell.run.return_value = (
            0,
            'OtherOS dummy 4.4.6 #1 SMP Wed Mar 16 22:13:40 UTC 2016 x86_64 '
            'x86_64 x86_64 Some/OS'
        )
        guest_obj = GuestLinux(
            system_name, host_name, user, passwd, extensions)

        # check if correctly raises the exception
        self.assertRaisesRegex(
            ConnectionError, '^Target system is not Linux$', guest_obj.login
        )

    # test_fail_flow_invalid_distro()

# TestGuestLinux
