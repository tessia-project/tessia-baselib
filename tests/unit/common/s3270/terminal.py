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
Terminal unittest
"""
# pylint: disable=no-member
#
# IMPORTS
#
from unittest.mock import patch
from unittest import TestCase
from tessia_baselib.common.s3270.terminal import Terminal
from tessia_baselib.common.s3270.exceptions import ZvmMessageError
#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
class TestTerminal(TestCase):
    """
    Unit test for the Terminal class
    """

    def setUp(self):
        """
        Mock S3270

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        self.s3270_patcher = patch(
            'tessia_baselib.common.s3270.terminal.S3270',
            autospec=True)
        self.mock_s3270 = self.s3270_patcher.start()
        self.addCleanup(self.s3270_patcher.stop)

        # set s3270 output
        self.mock_s3270.return_value.ascii.return_value = 'data: ok\n   \nok\n'
    # setUp()

    def test_connect_ok(self):
        """
        Exercise a normal connect command

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set s3270 output
        self.mock_s3270.return_value.query.return_value = 'data: \n     \nok\n'

        # create new instance of terminal
        terminal = Terminal()

        # simple command execution
        terminal.connect("hostname.com")
        self.assertEqual('hostname.com', terminal.host_name)
    # test_connect_ok()

    def test_connect_second_time(self):
        """
        Exercise a normal connect command

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set s3270 output
        self.mock_s3270.return_value.query.side_effect = [
            'data: host hostname.com 23\nU F U C(hostname.com) \nok\n'
        ]

        # create new instance of terminal
        terminal = Terminal()

        # simple command execution
        terminal.connect("hostname.com")
        terminal.connect("hostname.com")
        self.assertEqual('hostname.com', terminal.host_name)
        self.mock_s3270.return_value.disconnect.assert_called_once_with()
    # test_connect_second_time()

    def test_login_ok(self):
        """
        Exercise a normal login command

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of terminal
        terminal = Terminal()

        # simple command execution
        output = terminal.login("hostname.com", "user", "password")
        self.assertEqual(' ok\n', output)
    # test_login_ok()

    def test_login_already_logged_on(self):
        """
        Exercise a login when user is already logged on

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set s3270 output
        (self.mock_s3270.return_value
         .ascii.return_value) = 'data: HCPLGA054E\nok\n'

        # create new instance of terminal
        terminal = Terminal()

        # simple command execution
        self.assertRaises(ZvmMessageError, terminal.login,
                          'test.host.com', 'user', 'password')
    # test_login_already_logged_on()

    def test_login_with_open_connection(self):
        """
        Exercise a login when a connection is already in place

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        (self.mock_s3270.return_value
         .ascii.return_value) = 'data: ok\nL U U\nok\n'

        # create new instance of terminal
        terminal = Terminal()

        # simple command execution
        terminal.connect("hostname.com")
        output = terminal.login("hostname.com", "user", "password")
        self.assertEqual(' ok\n', output)
    # test_login_with_open_connection()

    def test_login_with_logonby(self):
        """
        Exercise a login with byuser

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of terminal
        terminal = Terminal()

        # simple command execution
        terminal.connect("hostname.com")
        output = terminal.login("hostname.com", "user", "password",
                                parameters={"byuser":"newuser"})
        self.assertEqual(' ok\n', output)
        (self.mock_s3270.return_value
         .string.assert_any_call("l user by newuser"))
    # test_login_with_logonby()

    def test_login_here(self):
        """
        Exercise a login here

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of terminal
        terminal = Terminal()

        # simple command execution
        terminal.connect("hostname.com")
        output = terminal.login("hostname.com", "user", "password",
                                parameters={"here":True})
        self.assertEqual(' ok\n', output)
        (self.mock_s3270.return_value
         .string.assert_any_call("l user here"))
    # test_login_here()

    def test_parse_output_placeholder(self):
        """
        Placeholder for _parse_output

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of terminal
        terminal = Terminal()

        # simple command execution
        self.assertRaises(NotImplementedError, terminal._parse_output, "text")
    # test_parse_output_placeholder()



# TestTerminal
