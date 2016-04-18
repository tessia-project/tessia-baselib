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
    def _checkInit(self):
        """
        Check if the class constructor works as expected and return the object
        for further testing.

        Args:
            None

        Returns:
            instance of GuestLinux

        Raises:
            AssertionError: if validation fails
        """
        # instantiate the guest class we want to test
        system_name = 'dummy_system'
        host_name = 'dummy.domain.com'
        user = 'root'
        passwd = 'somepwd'
        extensions = {}
        guestObj = GuestLinux(system_name, host_name, user, passwd, extensions)

        # validate if attributes were correctly assigned to object
        self.assertEqual('linux', guestObj.GUEST_ID)
        self.assertIs(system_name, guestObj.name)
        self.assertIs(host_name, guestObj.host_name)
        self.assertIs(user, guestObj.user)
        self.assertIs(passwd, guestObj.passwd)
        self.assertIs(extensions, guestObj.extensions)

        # return object for further testing
        return guestObj
    # _checkInit()

    def _checkLogin(self, guestObj, mockSshClientClass, mockSshClient,
                    mockSshShell, distro_name, distro_cmd):
        """
        Check if the login() method works as expected

        Args:
            guestObj: instance of GuestLinux
            mockSshClientClass: the mock created for class SshClient
            mockSshClient: the mock created for object of SshClient
            mockSshShell: the mock created for object of SshShell
            distro_name: name of distro class that should be created
            distro_cmd: expected command used to identify environment

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        # perform login to exercise distro detection
        guestObj.login()

        # validate if instantiating SshClient was correct
        mockSshClientClass.assert_called_with()

        # validate usage of SshClient object was correct
        mockSshClient.login.assert_called_with(
            guestObj.host_name,
            user=guestObj.user,
            passwd=guestObj.passwd,
            timeout=60
        )
        mockSshClient.openShell.assert_called_with()

        # validate if the right distro object was created
        self.assertIs(distro_name, guestObj._distroObj.__class__.__name__)

        # validate the right command was issued for env detection
        mockSshShell.run.assert_called_with(distro_cmd)

    # _checkLogin()

    def _checkLogoff(self, guestObj, mockSshClient):
        """
        Check if the logoff() method works as expected

        Args:
            guestObj: instance of GuestLinux
            mockSshClient: the mock created for object of SshClient

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        # call method and verify if it correctly drops distro object and
        # closes ssh connection
        guestObj.logoff()
        self.assertIs(None, guestObj._distroObj)
        mockSshClient.logoff.assert_called_with()
    # _checkLogoff()

    def _checkOpenSession(self, guestObj):
        """
        Check if the openSession() method works as expected

        Args:
            guestObj: instance of GuestLinux

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        sessionObj = guestObj.openSession()
        self.assertIs('GuestSessionLinux', sessionObj.__class__.__name__)
    # _checkOpenSession()

    def _checkStop(self, guestObj, mockSshShell, stop_cmd):
        """
        Check if the stop() method works as expected

        Args:
            guestObj: instance of GuestLinux
            mockSshShell: the mock created for object of SshShell
            stop_cmd: expected command used to shutdown system

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        # call method and verify if it executed cmd in ssh shell
        guestObj.stop()
        mockSshShell.run.assert_called_with(stop_cmd)
    # _checkStop()

    # mock the ssh module to pretend we connect to a real system
    @patch('tessia_baselib.guests.linux.linux.SshClient', spec_set=True)
    def testNormalFlowGenericDistro(self, mockSshClientClass):
        """
        Exercise a normal flow for a generic linux guest.

        Args:
            mockSshClientClass: the mock representing the SshClient class

        Returns:
            None

        Raises:
            AssertionError: if the guest object does not behave as expected
        """
        # set a simple log configuration to catch messages from all levels
        # and output to a file which we will check later
        logFile = NamedTemporaryFile()
        logging.basicConfig(filename=logFile.name, filemode='w',
                            level=logging.DEBUG)

        # define the mock for SshShell with only the run method which returns a
        # successful exit code and the below string response to a 'uname -a' cmd
        mockSshShell = Mock(name='SshShell', spec_set=['run'])
        mockSshShell.run.return_value = (
            0,
            'Linux dummy 4.4.6-200.x86_64 #1 SMP Wed Mar 16 22:13:40 UTC 2016 '
            'x86_64 x86_64 x86_64 GNU/Linux'
        )

        # define a SshClient object which will return the SshShell mock created
        # in previous step
        mockSshClient = Mock(
            name='SshClient', spec_set=['login', 'logoff', 'openShell']
        )
        mockSshClient.openShell.return_value = mockSshShell

        # make the mock SshClientClass from patch decorator return the object
        # we just defined upon instantiation
        mockSshClientClass.return_value = mockSshClient

        # validate the constructor of the guest class
        guestObj = self._checkInit()

        # validate login() method
        self._checkLogin(
            guestObj, mockSshClientClass, mockSshClient, mockSshShell,
            'DistroGeneric', 'uname -a'
        )

        # validate openSession() method
        self._checkOpenSession(guestObj)

        # validate stop() method
        self._checkStop(guestObj, mockSshShell, 'nohup halt &')

        # validate logoff() method
        self._checkLogoff(guestObj, mockSshClient)

        # validate the logging was correct
        # define the content we expect to see in the log file
        log_prefix = 'DEBUG:tessia_baselib.guests.linux.linux'
        expected_log = (
            "{0}:create GuestLinux: name='{1.name}' host_name='{1.host_name}' "
            "user='{1.user}' extensions='{1.extensions}'\n".format(
                log_prefix, guestObj)
        )
        expected_log += (
            "{}:create distro system_name='{}' distro_obj='DistroGeneric'\n"
            .format(log_prefix, guestObj.name)
        )
        expected_log += (
            "{}:logoff system_name='{}'\n".format(log_prefix, guestObj.name)
        )
        # retrieve the content written in the log file
        logRead = open(logFile.name, 'r')
        actual_log = logRead.read()
        logRead.close()
        # allow unittest class to show the full diff in case of error
        self.maxDiff = None
        # perform the comparison to validate the content
        self.assertEqual(expected_log, actual_log)

    # test_normal_flow_generic_distro()

    # mock the ssh module to pretend we connect to a real system
    @patch('tessia_baselib.guests.linux.linux.SshClient', spec_set=True)
    def testFailFlowInvalidDistro(self, mockSshClientClass):
        """
        Simulate the connection to a system which does not claim to have a
        Linux kernel.

        Args:
            mockSshClientClass: the mock representing the SshClient class

        Returns:
            None

        Raises:
            AssertionError: if guest object does not raise NotImplementedError
                            for the called methods
        """
        # define the mock for SshShell with only the run method which fails to
        # execute commands
        mockSshShell = Mock(name='SshShell', spec_set=['run'])
        mockSshShell.run.return_value = (1, 'command not found')

        # SshClient instance which will return the SshShell mock we just
        # defined
        mockSshClient = Mock(name='SshClient', spec_set=['login', 'openShell'])
        mockSshClient.openShell.return_value = mockSshShell

        # make the mock SshClientClass from patch decorator return the object
        # we just defined upon instantiation
        mockSshClientClass.return_value = mockSshClient

        # instantiate the guest class we want to test
        system_name = 'dummy_system'
        host_name = 'dummy.domain.com'
        user = 'root'
        passwd = 'somepwd'
        extensions = {}
        guestObj = GuestLinux(system_name, host_name, user, passwd, extensions)

        # check if correctly raises the exception
        self.assertRaises(ConnectionError, guestObj.login)

        # change the mock now to successfully execute the command but report an
        # incorrect kernel name
        mockSshShell.run.return_value = (
            0,
            'OtherOS dummy 4.4.6 #1 SMP Wed Mar 16 22:13:40 UTC 2016 x86_64 '
            'x86_64 x86_64 Some/OS'
        )
        guestObj = GuestLinux(system_name, host_name, user, passwd, extensions)

        # check if correctly raises the exception
        self.assertRaisesRegex(
            ConnectionError, '^Target system is not Linux$', guestObj.login
        )

    # test_fail_flow_invalid_distro()

# TestGuestLinux
