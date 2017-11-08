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
# pylint: disable=no-member,attribute-defined-outside-init
#
# IMPORTS
#
from unittest.mock import patch
from unittest import TestCase
from tessia.baselib.common.s3270.terminal import Terminal
from tessia.baselib.common.s3270.exceptions import ZvmMessageError
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

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        self.s3270_patcher = patch(
            'tessia.baselib.common.s3270.terminal.S3270',
            autospec=True)
        self.mock_s3270 = self.s3270_patcher.start()
        self.addCleanup(self.s3270_patcher.stop)

        # set s3270 output
        (self.mock_s3270.return_value
         .ascii.return_value) = 'data: ok\ndata: RUNNING\n'
    # setUp()

    def test_connect_ok(self):
        """
        Exercise a normal connect command

        Args:
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

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set s3270 output
        self.mock_s3270.return_value.ascii.side_effect = [
            'data: ok\nU F U C(hostname.com) \nok\n',
            'data: VM READ\nok\n',
            'data: ok\ndata: RUNNING\nU F U C(hostname.com) \nok\n',
        ]

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

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        (self.mock_s3270.return_value
         .ascii.return_value) = 'data: ok\ndata: RUNNING\nL U U\nok\n'

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

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set s3270 output
        self.mock_s3270.return_value.ascii.side_effect = [
            'data: ok\nU F U C(hostname.com) \nok\n',
            'data: CP READ\nok\n',
            'data: ok\ndata: RUNNING\nU F U C(hostname.com) \nok\n',
        ]
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

    def test_disconnect_ok(self):
        """
        Exercise a normal disconnect command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set s3270 output
        self.mock_s3270.return_value.ascii.side_effect = [
            'data: ok\nU F U C(hostname.com) \nok\n',
            'data: VM READ\nok\n',
            'data: ok\nU F U C(hostname.com) \nok\n',
        ]

        # create new instance of terminal
        terminal = Terminal()

        # simple command execution
        output = terminal.login("hostname.com", "user", "password")
        output = terminal.disconnect()

        self.assertIs(output, True)
    # test_disconnect_ok()

    def test_disconnect_with_problem(self):
        """
        Exercise a disconnect that fails keeping connected

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set s3270 output
        self.mock_s3270.return_value.ascii.side_effect = [
            'data: ok\nU F U C(hostname.com) \nok\n',
            'data: VM READ\nok\n',
            'data: ok\nU F U C(hostname.com) \nok\n',
        ]
        # set s3270 output
        self.mock_s3270.return_value.query.side_effect = [
            'data: host hostname.com 23\nU F U C(hostname.com) \nok\n'
        ]

        # create new instance of terminal
        terminal = Terminal()

        # simple command execution
        output = terminal.login("hostname.com", "user", "password")
        output = terminal.disconnect()

        self.assertIs(output, False)
    # test_disconnect_with_problem()

    def test_logoff_ok(self):
        """
        Exercise a normal logoff command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set s3270 output
        self.mock_s3270.return_value.ascii.side_effect = [
            'data: ok\nU F U C(hostname.com) \nok\n',
            'data: VM READ\nok\n',
            'data: ok\nU F U C(hostname.com) \nok\n',
        ]

        # create new instance of terminal
        terminal = Terminal()

        # simple command execution
        output = terminal.login("hostname.com", "user", "password")
        output = terminal.logoff()

        self.assertIs(output, True)
    # test_logoff_ok()

    def test_logoff_with_problem(self):
        """
        Exercise a logoff that fails keeping connected

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set s3270 output
        self.mock_s3270.return_value.ascii.side_effect = [
            'data: ok\nU F U C(hostname.com) \nok\n',
            'data: VM READ\nok\n',
            'data: ok\nU F U C(hostname.com) \nok\n',
        ]
        # set s3270 output
        self.mock_s3270.return_value.query.side_effect = [
            'data: host hostname.com 23\nU F U C(hostname.com) \nok\n'
        ]

        # create new instance of terminal
        terminal = Terminal()

        # simple command execution
        output = terminal.login("hostname.com", "user", "password")
        output = terminal.logoff()

        self.assertIs(output, False)
    # test_logoff_with_problem()

    def test_send_cmd_cms(self):
        """
        Exercise send_cmd with a CMS command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set s3270 output
        self.mock_s3270.return_value.query.side_effect = [
            'data: host hostname.com 23\nU F U C(hostname.com) \nok\n',
        ]

        self.mock_s3270.return_value.ascii.side_effect = [
            'data: \nU F U C(hostname.com) \nok\n', # middle of login method
            'data: \nU F U C(hostname.com) \nok\n', # _check_status at login
            'data: \nU F U C(hostname.com) \nok\n', # end of login method
            'data: MORE...             \nU F U C(hostname.com) \nok\n',
            'data: HOLDING             \nU F U C(hostname.com) \nok\n',
            'data: profile\ndata: Ready;\nU F U C(hostname.com) \nok\n',

        ]

        # create new instance of terminal
        terminal = Terminal()

        # simple command execution
        terminal.login("hostname.com", "user", "password")

        cmd_output = terminal.send_cmd("profile", wait_for="Ready;")
        content = " profile\n"
        self.assertEqual(content, cmd_output[0])
    # test_send_cmd_cms()

    def test_send_cmd_cms_with_timeout(self):
        """
        Exercise send_cmd with a CMS command when a timeout occurs

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set s3270 output
        self.mock_s3270.return_value.query.side_effect = [
            'data: host hostname.com 23\nU F U C(hostname.com) \nok\n',
        ]

        self.mock_s3270.return_value.ascii.side_effect = [
            'data: \nU F U C(hostname.com) \nok\n', # middle of login method
            'data: \nU F U C(hostname.com) \nok\n', # _check_status at login
            'data: \nU F U C(hostname.com) \nok\n', # end of login method
            'data: MORE...             \nU F U C(hostname.com) \nok\n',
            'data: HOLDING             \nU F U C(hostname.com) \nok\n',
            'data: profile\ndata: Ready;\nU F U C(hostname.com) \nok\n',

        ]

        self.time_patcher = patch('time.time', autospec=True)
        self.mock_time = self.time_patcher.start()
        self.addCleanup(self.time_patcher.stop)

        self.mock_time.side_effect = [
            1475010078.6838996,
            1475010111.7996376,
            1475010511.7996376,
        ]

        # create new instance of terminal
        terminal = Terminal()

        # simple command execution
        terminal.login("hostname.com", "user", "password")

        cmd_output = terminal.send_cmd("profile", wait_for="Ready;")
        self.assertIs(cmd_output[1], True)
    # test_send_cmd_cms_with_timeout()

    def test_send_cmd_cp(self):
        """
        Exercise send_cmd with a CP command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set s3270 output
        self.mock_s3270.return_value.query.side_effect = [
            'data: host hostname.com 23\nU F U C(hostname.com) \nok\n',
        ]

        self.mock_s3270.return_value.ascii.side_effect = [
            'data: \nU F U C(hostname.com) \nok\n',
            'data: \nU F U C(hostname.com) \nok\n',
            'data: \nU F U C(hostname.com) \nok\n',
            'data: profile\ndata: Ready;\nU F U C(hostname.com) \nok\n',
        ]

        # create new instance of terminal
        terminal = Terminal()

        # simple command execution
        terminal.login("hostname.com", "user", "password")

        cmd_output = terminal.send_cmd("profile", True)
        self.assertEqual(' profile\n', cmd_output[0])
    # test_send_cmd_cp()

    def test_send_cmd_without_connection(self):
        """
        Exercise send_cmd without a conneciton to host

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set s3270 output
        self.mock_s3270.return_value.query.side_effect = [
            'data: host hostname.com 23\nU F U C(hostname.com) \nok\n',
        ]

        self.mock_s3270.return_value.ascii.side_effect = [
            'data: \nU F U C(hostname.com) \nok\n',
            'data: \nU F U C(hostname.com) \nok\n',
            'data: \nU F U C(hostname.com) \nok\n',
            'data: profile\ndata: Ready;\nU F U C(hostname.com) \nok\n',
        ]

        # create new instance of terminal
        terminal = Terminal()

        self.assertRaises(RuntimeError, terminal.send_cmd,
                          'profile', True)
    # test_send_cmd_without_connection()

# TestTerminal
