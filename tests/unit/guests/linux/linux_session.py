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
Unit test for module linux_session
"""

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
        mock_ssh_shell = Mock(name='SshShell', spec_set=['close', 'run'])
        mock_ssh_shell.run.return_value = (0, 'dummy output')

        # instantiate the session class we want to test
        session_obj = GuestSessionLinux(mock_ssh_shell)

        # simple command execution
        ret, output = session_obj.run('ls /etc')
        self.assertEqual(0, ret)
        self.assertEqual('dummy output', output)

        # validate it
        mock_ssh_shell.run.assert_called_with('ls /etc', 120)

        # command with timeout specified
        mock_ssh_shell.run.return_value = (0, 'another dummy output')
        ret, output = session_obj.run('cat /etc/passwd', timeout=10)

        # validate it
        self.assertEqual(0, ret)
        self.assertEqual('another dummy output', output)
        mock_ssh_shell.run.assert_called_with('cat /etc/passwd', 10)

        # test a failed command
        mock_ssh_shell.run.return_value = (1, 'error dummy output')
        ret, output = session_obj.run('errorcmd')

        # validate it
        self.assertEqual(1, ret)
        self.assertEqual('error dummy output', output)
        mock_ssh_shell.run.assert_called_with('errorcmd', 120)

        # make sure clean up is correct upon closing session
        session_obj.close()
        mock_ssh_shell.close.assert_called_with()
        self.assertIs(None, session_obj._ssh_shell)
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
        mock_ssh_shell = Mock(name='SshShell', spec_set=['close', 'run'])
        mock_ssh_shell.run.side_effect = SshShellError(
            'dummy unexpected error')

        # create session object
        session_obj = GuestSessionLinux(mock_ssh_shell)

        # validate behavior when internal error occurs
        self.assertRaisesRegex(
            RuntimeError,
            '^dummy unexpected error$',
            session_obj.run,
            'dummycmd'
        )

        # validate behavior when timeout occurs
        # pylint: disable=redefined-variable-type
        mock_ssh_shell.run.side_effect = TimeoutError('dummy timeout error')
        self.assertRaisesRegex(
            TimeoutError,
            '^dummy timeout error$',
            session_obj.run,
            'dummycmd'
        )
    # test_error_cmds()

# TestGuestLinux
