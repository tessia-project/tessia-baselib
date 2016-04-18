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
from tessia_baselib.guests.linux.linux_session import GuestSessionLinux
from unittest import TestCase
from unittest.mock import Mock

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

class TestGuestLinux(TestCase):
    """
    Unit test for the GuestSessionLinux class
    """
    def test_normal_cmds(self):
        """
        Exercise a normal execution of a command

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # define the mock for SshShell with the close and run methods which
        # returns a successful response
        mockSshShell = Mock(name='SshShell', spec_set=['close', 'run'])
        mockSshShell.run.return_value = (0, 'dummy output')

        # instantiate the session class we want to test
        sessionObj = GuestSessionLinux(mockSshShell)

        # simple command execution
        ret, output = sessionObj.run('ls /etc')
        self.assertEqual(0, ret)
        self.assertEqual('dummy output', output)

        # validate it
        mockSshShell.run.assert_called_with('ls /etc', 120)

        # command with timeout specified
        mockSshShell.run.return_value = (0, 'another dummy output')
        ret, output = sessionObj.run('cat /etc/passwd', timeout=10)

        # validate it
        self.assertEqual(0, ret)
        self.assertEqual('another dummy output', output)
        mockSshShell.run.assert_called_with('cat /etc/passwd', 10)

        # test a failed command
        mockSshShell.run.return_value = (1, 'error dummy output')
        ret, output = sessionObj.run('errorcmd')

        # validate it
        self.assertEqual(1, ret)
        self.assertEqual('error dummy output', output)
        mockSshShell.run.assert_called_with('errorcmd', 120)

        # make sure clean up is correct upon closing session
        sessionObj.close()
        mockSshShell.close.assert_called_with()
        self.assertIs(None, sessionObj._sshShell)
    # test_normal_cmds()

    def test_error_cmds(self):
        """
        Simulate problems when trying to execute the commands

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if session does not fail as expected
        """
        # define the mock for SshShell with only the run method which fails to
        # execute commands
        mockSshShell = Mock(name='SshShell', spec_set=['close', 'run'])
        mockSshShell.run.side_effect = SshShellError('dummy unexpected error')

        # create session object
        sessionObj = GuestSessionLinux(mockSshShell)

        # validate behavior when internal error occurs
        self.assertRaisesRegex(
            RuntimeError,
            '^dummy unexpected error$',
            sessionObj.run,
            'dummycmd'
        )

        # validate behavior when timeout occurs
        mockSshShell.run.side_effect = TimeoutError('dummy timeout error')
        self.assertRaisesRegex(
            TimeoutError,
            '^dummy timeout error$',
            sessionObj.run,
            'dummycmd'
        )
    # test_error_cmds()

# TestGuestLinux
