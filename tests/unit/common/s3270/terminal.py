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
#
# IMPORTS
#
from tessia.baselib.common.s3270 import terminal
from tessia.baselib.common.s3270.exceptions import S3270StatusError
from tessia.baselib.common.s3270.exceptions import ZvmMessageError
from unittest import mock
from unittest import TestCase
from unittest.mock import patch

import os
import yaml

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

    @classmethod
    def setUpClass(cls):
        """
        Store the console output data to be used in the tests.
        """
        data_file = '{}/terminal.yaml'.format(
            os.path.dirname(os.path.abspath(__file__)))
        with open(data_file, 'r', encoding='utf-8') as data_fd:
            cls._data = yaml.safe_load(data_fd.read())
    # setUpClass()

    def setUp(self):
        """
        Mock S3270
        """
        # patch the S3270 object
        patcher = patch.object(terminal, 'S3270', autospec=True)
        self._mock_s3270 = patcher.start().return_value
        self._mock_s3270.host_name = None
        def mock_connect(host_name, *_, **__):
            """
            Set the hostname when called, like the original method.
            """
            self._mock_s3270.host_name = host_name
        self._mock_s3270.connect = mock_connect
        self.addCleanup(patcher.stop)

        # patch the logger object
        patcher = patch.object(terminal, 'get_logger', autospec=True)
        self._mock_logger = patcher.start().return_value
        self.addCleanup(patcher.stop)

        # patch time.time
        patcher = patch.object(terminal, 'time', autospec=True)
        self._mock_time = patcher.start()
        self.addCleanup(patcher.stop)
        def time_gen():
            """
            Generator to simulate a call to time.time()
            """
            start = 1.0
            while True:
                yield start
                start += 0.5
        # time_gen
        mock_time = time_gen()
        self._mock_time.side_effect = lambda: next(mock_time)

        # patch sleep
        patcher = patch.object(terminal, 'sleep', autospec=True)
        patcher.start()
        self.addCleanup(patcher.stop)

        # set s3270 output
        self._mock_s3270.ascii.return_value = 'data: ok\ndata: RUNNING\n'

        # instance of terminal for convenience
        self._term = terminal.Terminal()
    # setUp()

    def test_cmds_without_connection(self):
        """
        Exercise executing various commands without a connection established to
        the host
        """
        # set s3270 output
        self._mock_s3270.query.return_value = (
            'data:                             \n'
            'L U U N N 4 24 80 0 0 0x0 -                    \n'
            'ok                           \n'
        )

        # no connection means no hostname set
        self.assertIs(self._term.host_name, None)

        with self.assertRaises(RuntimeError):
            self._term.disconnect()
        with self.assertRaises(RuntimeError):
            self._term.logoff()
        with self.assertRaises(RuntimeError):
            self._term.send_cmd('any_command')
        with self.assertRaises(RuntimeError):
            self._term.transfer('any_command')
    # test_cmds_without_connection()

    def test_connect_ok(self):
        """
        Exercise a normal connect command
        """
        # set s3270 output
        self._mock_s3270.query.return_value = 'data: \n     \nok\n'

        self._term.connect("hostname.com")
        self.assertEqual('hostname.com', self._term.host_name)
    # test_connect_ok()

    def test_connect_second_time(self):
        """
        Exercise a connect executed two times, the first connection should be
        dropped and a new one established.
        """
        # set s3270 output
        self._mock_s3270.query.side_effect = [
            'data: host hostname.com 23\nU F U C(hostname.com) \nok\n'
        ]

        self._term.connect("hostname.com")
        self._term.connect("hostname.com")
        self.assertEqual('hostname.com', self._term.host_name)
        self._mock_s3270.disconnect.assert_called_once_with()
    # test_connect_second_time()

    def test_disconnect(self):
        """
        Exercise a normal disconnect command
        """
        self._mock_s3270.ascii.side_effect = self._data['login_ok']
        self._mock_s3270.query.side_effect = [
            'data: host hostname.com 23\nU F U C(hostname.com) \nok\n',
            'data: \nL U U N N 4 24 80 0 0 0x0 -\nok\n'
        ]

        # perform action
        self._term.login("hostname.com", "user", "password")
        self._term.disconnect()

        # validate behavior
        self._mock_s3270.quit.assert_called_once_with()
        self.assertEqual(self._mock_s3270.string.mock_calls, [
            mock.call('l user'),
            mock.call('password', hide=True),
            mock.call('#cp term more 50 10'),
            mock.call('#cp disconnect'),
        ])
    # test_disconnect()

    def test_empty_output(self):
        """
        Test the scenario where a command generates empty output. Should not
        happen in real usage as the ascii() always returns some output but it
        is worth to validate that the code can handle such case.
        """
        self._mock_s3270.ascii.side_effect = self._data['login_ok']
        self._mock_s3270.query.side_effect = [
            'data: host hostname.com 23\nU F U C(hostname.com) \nok\n'
        ]

        # perform action
        self._term.login("hostname.com", "user", "password")
        self._mock_s3270.ascii.side_effect = None
        self._mock_s3270.ascii.return_value = ''
        output = self._term.send_cmd("dummy")

        # validate behavior
        self.assertEqual(output, ('', None))
        self.assertEqual(self._mock_s3270.string.mock_calls, [
            mock.call('l user'),
            mock.call('password', hide=True),
            mock.call('#cp term more 50 10'),
            mock.call('dummy'),
        ])
    # test_empty_output()

    def test_login_already_logged_on(self):
        """
        Exercise a login when user is already logged on
        """
        # set s3270 output
        self._mock_s3270.ascii.side_effect = self._data['login_already_logged']

        # validate result
        with self.assertRaisesRegex(ZvmMessageError, 'Already logged'):
            self._term.login('hostname.com', 'user', 'password')

        # validate behavior (commands entered)
        self.assertEqual(self._mock_s3270.string.mock_calls, [
            mock.call('l user'),
            mock.call('password', hide=True),
        ])
    # test_login_already_logged_on()

    def test_login_generic_error(self):
        """
        Exercise the scenario where a generic error message occurs during logon
        """
        # set s3270 output
        self._mock_s3270.ascii.side_effect = self._data['login_generic_error']

        # validate result
        error_msg = 'HCP052E Error in CP directory'
        with self.assertRaisesRegex(ZvmMessageError, error_msg):
            self._term.login('hostname.com', 'user', 'password')

        # validate behavior (commands entered)
        self.assertEqual(self._mock_s3270.string.mock_calls, [
            mock.call('l user'),
        ])

        # test whether the generic error regex also catches an error without
        # description
        self._mock_s3270.ascii.side_effect = self._data[
            'login_generic_error_no_desc']
        with self.assertRaisesRegex(ZvmMessageError, 'HCP003E $'):
            self._term.login('hostname.com', 'user', 'password')

    # test_login_generic_error()

    def test_login_ok(self):
        """
        Exercise a normal login command
        """
        # set s3270 output
        self._mock_s3270.ascii.side_effect = self._data['login_ok']

        # perform action
        output = self._term.login("hostname.com", "user", "password")

        # validate result
        self.assertIn('RECONNECTED AT', output)

        # validate behavior (commands entered)
        self.assertEqual(self._mock_s3270.string.mock_calls, [
            mock.call('l user'),
            mock.call('password', hide=True),
            mock.call('#cp term more 50 10'),
        ])
    # test_login_ok()

    def test_login_ok_cp_read(self):
        """
        Exercise a normal login command where terminal waits in CP READ (as we
        specify noipl). This test also covers usage of extra parameters for
        login.
        """
        # set s3270 output
        self._mock_s3270.ascii.side_effect = self._data['login_ok_cp_read']

        # perform action
        output = self._term.login("hostname.com", "user", "password",
                                  parameters={"here": True, "noipl": True})

        # validate result
        self.assertIn('RECONNECTED AT', output)

        # validate behavior (commands entered)
        self.assertListEqual(self._mock_s3270.string.mock_calls, [
            mock.call('l user here noipl'),
            mock.call('password', hide=True),
            mock.call('begin'),
            mock.call('#cp term more 50 10'),
        ])
    # test_login_ok_cp_read()

    def test_login_ok_pending(self):
        """
        Exercise a normal login command where guest reports LOGOFF/FORCE
        pending after user is entered and after a few tries we get logged off
        by the hypervisor. This test also covers the case where CMS is ipled
        automatically after the login.
        """
        # set query to return we are disconnected in order to simulate the
        # logoff by the hypervisor
        self._mock_s3270.query.return_value = (
            'data:                             \n'
            'L U U N N 4 24 80 0 0 0x0 -                    \n'
            'ok                           \n'
        )

        # set s3270 output
        self._mock_s3270.ascii.side_effect = self._data[
            'login_ok_pending']

        # perform action
        hostname = 'hostname.com'
        output = self._term.login(hostname, "user", "password")

        # validate result
        self.assertIn('LOGON AT', output)

        # validate behavior (commands entered)
        self.assertEqual(
            self._mock_s3270.string.mock_calls,
            (4 * [mock.call('l user')]) + [mock.call('password', hide=True)] +
            [mock.call('#cp term more 50 10')]
        )
        self._mock_s3270.query.assert_called_with()
    # test_login_ok_pending()

    def test_login_ok_pending_after_pwd(self):
        """
        Exercise a normal login command where guest reports LOGOFF/FORCE
        pending after password is entered. This test also covers the case where
        CMS is ipled automatically after the login.
        """
        # set s3270 output
        self._mock_s3270.ascii.side_effect = self._data[
            'login_ok_pending_after_pwd']

        # perform action
        output = self._term.login("hostname.com", "user", "password")

        # validate result
        self.assertIn('LOGON AT', output)

        # validate behavior (commands entered)
        self.assertEqual(self._mock_s3270.string.mock_calls, [
            mock.call('l user'),
            mock.call('password', hide=True),
            mock.call('l user'),
            mock.call('password', hide=True),
            mock.call('#cp term more 50 10'),
        ])
    # test_login_ok_pending_after_pwd()

    def test_login_pending_forever(self):
        """
        Exercise the scenario where the pending user is never released.
        """
        # set s3270 output
        self._mock_s3270.ascii.return_value = self._data[
            'login_ok_pending'][0]

        # perform action
        error_msg = 'LOGOFF/FORCE pending for user'
        with self.assertRaisesRegex(TimeoutError, error_msg):
            self._term.login("hostname.com", "user", "password")
    # test_login_pending_forever()

    def test_login_with_open_connection(self):
        """
        Exercise a login when a connection is already in place
        """
        # set s3270 output
        self._mock_s3270.query.side_effect = [
            'data: host hostname.com 23\nU F U C(hostname.com) \nok\n'
        ]
        self._mock_s3270.ascii.side_effect = self._data['login_ok']

        # perform action
        self._term.connect("hostname.com")
        output = self._term.login("hostname.com", "user", "password")

        # validate result
        self.assertIn('RECONNECTED AT', output)

        # validate behavior
        self.assertEqual(self._mock_s3270.string.mock_calls, [
            mock.call('l user'),
            mock.call('password', hide=True),
            mock.call('#cp term more 50 10'),
        ])
    # test_login_with_open_connection()

    def test_login_with_logonby(self):
        """
        Exercise a login with byuser
        """
        self._mock_s3270.ascii.side_effect = self._data['login_ok']

        # perform action
        self._term.connect("hostname.com")
        output = self._term.login("hostname.com", "user", "password",
                                  parameters={"byuser":"newuser"})

        # validate result
        self.assertIn('RECONNECTED AT', output)

        # validate behavior
        self.assertEqual(self._mock_s3270.string.mock_calls, [
            mock.call('l user by newuser'),
            mock.call('password', hide=True),
            mock.call('#cp term more 50 10'),
        ])
    # test_login_with_logonby()

    def test_login_wrong_password(self):
        """
        Exercise wrong password provided at logon
        """
        # set s3270 output
        self._mock_s3270.ascii.side_effect = self._data['login_wrong_password']

        # validate result
        error_msg = 'incorrect userid and/or password'
        with self.assertRaisesRegex(PermissionError, error_msg):
            self._term.login('hostname.com', 'user', 'password')

        # validate behavior
        self.assertEqual(self._mock_s3270.string.mock_calls, [
            mock.call('l user'),
            mock.call('password', hide=True),
        ])
    # test_login_wrong_password()

    def test_logoff_ok(self):
        """
        Exercise a normal logoff command
        """
        # set s3270 output
        self._mock_s3270.ascii.side_effect = self._data['login_ok']
        self._mock_s3270.query.side_effect = [
            'data: host hostname.com 23\nU F U C(hostname.com) \nok\n',
            'data: \nL U U N N 4 24 80 0 0 0x0 -\nok\n'
        ]

        # perform action
        self._term.login("hostname.com", "user", "password")
        self._term.logoff()

        # validate behavior
        self._mock_s3270.quit.assert_called_once_with()
        self.assertEqual(self._mock_s3270.string.mock_calls, [
            mock.call('l user'),
            mock.call('password', hide=True),
            mock.call('#cp term more 50 10'),
            mock.call('#cp logoff'),
        ])
    # test_logoff_ok()

    def test_send_cmd_cms(self):
        """
        Exercise send_cmd with a CMS command
        """
        # set return value so that the connection appears to be always
        # active
        self._mock_s3270.query.return_value = (
            'data: host hostname.com 23\nU F U C(hostname.com) \nok\n'
        )
        # set s3270 output
        self._mock_s3270.ascii.side_effect = (
            self._data['login_ok'] + self._data['send_cmd_cms'])

        # start cms
        self._term.login("hostname.com", "user", "password")
        re_wait_for = 'Ready;'
        output, re_match = self._term.send_cmd(
            'i cms', use_cp=True, wait_for=[re_wait_for])
        # raises attribute error in case nothing was matched
        self.assertEqual(re_match.re.pattern, re_wait_for)
        # output check is according to the content in the yaml file
        self.assertIn('OSA  F5F2', output)

        # execute command
        output, re_match = self._term.send_cmd("profile", wait_for=re_wait_for)
        self.assertEqual(re_match.re.pattern, re_wait_for)
        # entry in the first 'page'
        self.assertIn('OSA  F5F4', output)
        # entry in the middle 'page'
        self.assertIn('OSA  F6F4', output)
        # entry in the last 'page'
        self.assertIn('OSA  F7F2', output)

        # validate behavior
        self.assertEqual(self._mock_s3270.string.mock_calls, [
            mock.call('l user'),
            mock.call('password', hide=True),
            mock.call('#cp term more 50 10'),
            mock.call('#cp i cms'),
            mock.call('profile'),
        ])
    # test_send_cmd_cms()

    def test_send_cmd_cms_no_wait_for(self):
        """
        Exercise send_cmd without wait_for to make sure all available output is
        consumed.
        """
        # set return value so that the connection appears to be always
        # active
        self._mock_s3270.query.return_value = (
            'data: host hostname.com 23\nU F U C(hostname.com) \nok\n'
        )
        # set s3270 output
        self._mock_s3270.ascii.side_effect = (
            self._data['login_ok'] + self._data['send_cmd_cms'])

        # start cms
        self._term.login("hostname.com", "user", "password")
        output, re_match = self._term.send_cmd(
            'i cms', use_cp=True)
        self.assertIs(re_match, None)
        # output check is according to the content in the yaml file
        self.assertIn('OSA  F5F2', output)

        # execute command
        output, re_match = self._term.send_cmd("profile")
        self.assertIs(re_match, None)
        # entry in the first 'page'
        self.assertIn('OSA  F5F4', output)
        # entry in the middle 'page'
        self.assertIn('OSA  F6F4', output)
        # entry in the last 'page'
        self.assertIn('OSA  F7F2', output)

        # validate behavior
        self.assertEqual(self._mock_s3270.string.mock_calls, [
            mock.call('l user'),
            mock.call('password', hide=True),
            mock.call('#cp term more 50 10'),
            mock.call('#cp i cms'),
            mock.call('profile'),
        ])
    # test_send_cmd_cms_no_wait_for()

    def test_send_cmd_cms_with_timeout(self):
        """
        Exercise send_cmd with a CMS command while setting a wait_for which
        never occurs.
        """
        # set return value so that the connection appear to be always
        # active
        self._mock_s3270.query.return_value = (
            'data: host hostname.com 23\nU F U C(hostname.com) \nok\n'
        )
        # set s3270 output
        self._mock_s3270.ascii.side_effect = (
            self._data['login_ok'] + self._data['send_cmd_cms'])

        # start cms
        self._term.login("hostname.com", "user", "password")
        # set a pattern that will never happen
        re_wait_for = 'THIS WILL NEVER HAPPEN'
        # set the timeout to loop the number of times needed to consume all the
        # 'side effect' output
        output, re_match = self._term.send_cmd(
            'i cms', use_cp=True, wait_for=[re_wait_for], timeout=2.6)
        # validate result - match is None as the expected output didn't happen
        self.assertEqual(re_match, None)
        # check whether all expected output was consumed
        self.assertIn('OSA  F5F2', output)
        # entry in the first 'page'
        self.assertIn('OSA  F5F4', output)
        # entry in the middle 'page'
        self.assertIn('OSA  F6F4', output)
        # entry in the last 'page'
        self.assertIn('OSA  F7F2', output)
    # test_send_cmd_cms_with_timeout()

    def test_transfer(self):
        """
        Test whether the transfer command is correctly executed.
        """
        # set s3270 output
        self._mock_s3270.ascii.side_effect = self._data['login_ok']
        self._mock_s3270.query.return_value = (
            'data: host hostname.com 23\nU F U C(hostname.com) \nok\n')

        # set mock to return output of transfer call
        self._mock_s3270.transfer.return_value = (
            'U U U C(hostname.com) I 4 24 80 0 0 0x0 0.008\n'
            'ok                                             \n'
        )

        # perform action
        args = ['/some/file', 'DEST FILE A']
        self._term.login("hostname.com", "user", "password")
        output = self._term.transfer(*args)
        # validate result
        self.assertEqual(output, '')
        # validate behavior
        self._mock_s3270.transfer.assert_called_with(*args)

        # try transfer with extra parameters
        kwargs = {
            'local_path': '/some/file',
            'remote_path': 'SRC FILE A',
            'direction': 'receive',
            'mode': 'ascii',
            'recfm': 'variable',
            'extra1': 'value1'
        }
        output = self._term.transfer(**kwargs)
        # validate result
        self.assertEqual(output, '')
        # validate behavior
        self._mock_s3270.transfer.assert_called_with(**kwargs)
    # test_transfer()

    def test_transfer_error(self):
        """
        Exercise a transfer command which fails.
        """
        # set s3270 output
        self._mock_s3270.ascii.side_effect = self._data['login_ok']
        self._mock_s3270.query.return_value = (
            'data: host hostname.com 23\nU F U C(hostname.com) \nok\n')

        # set mock to return output of transfer call
        base_error = "Local file '/some/file': No such file or directory"
        self._mock_s3270.transfer.side_effect = S3270StatusError(
            'Failed to execute Transfer command',
            "data: {}    \n"
            "U F U C(hostname.com) I 4 43 80 41 0 0x0 -\n"
            "error                                          \n".format(
                base_error)
        )

        # perform action
        args = ['/some/file', 'DEST FILE A']
        self._term.login("hostname.com", "user", "password")
        error_msg = 'Transfer failed, output: {}'.format(base_error)
        with self.assertRaisesRegex(RuntimeError, error_msg):
            self._term.transfer(*args)
    # test_transfer_error()

# TestTerminal
