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
S3270 unittest
"""

#
# IMPORTS
#
from unittest.mock import patch
from unittest import TestCase
from tessia.baselib.common.s3270.s3270 import S3270
from tessia.baselib.common.s3270.exceptions import S3270StatusError
#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
class TestS3270(TestCase):
    """
    Unit test for the S3270 class
    """

    def setUp(self):
        """
        Mock s3270pipeconnector

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        self.pipeconnector_patcher = patch(
            'tessia.baselib.common.s3270.s3270.S3270PipeConnector',
            autospec=True)
        self.mock_pipeconnector = self.pipeconnector_patcher.start()
        self.addCleanup(self.pipeconnector_patcher.stop)

        # set status to ok
        self.mock_pipeconnector.return_value.run.return_value = [
            'ok\n', 'L U U N N 4 24 80 0 0 0x0 -\nok\n'
        ]
    # setUp()

    def tearDown(self):
        #self.popen_patcher.stop()
        #self.poll_patcher.stop()
        pass
    # tearDown()

    def test_ascii_ok(self):
        """
        Exercise a normal ascii command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        output = s3270.ascii()
        self.assertEqual('L U U N N 4 24 80 0 0 0x0 -\nok\n', output)
    # test_ascii_ok()

    def test_ascii_with_parameters(self):
        """
        Exercise a normal ascii command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        output = s3270.ascii(' ')
        self.assertEqual('L U U N N 4 24 80 0 0 0x0 -\nok\n', output)
    # test_ascii_ok()

    def test_ascii_error(self):
        """
        Exercise an ascii command returning error

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to error
        self.mock_pipeconnector.return_value.run.return_value = [
            'error\n', 'L U U N N 4 24 80 0 0 0x0 -\nerror\n'
        ]
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(S3270StatusError, s3270.ascii)
    # test_ascii_error()

    def test_ascii_timeout(self):
        """
        Exercise an ascii command returning timeout

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to timeout
        self.mock_pipeconnector.return_value.run.side_effect = TimeoutError()

        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(TimeoutError, s3270.ascii)
    # test_ascii_timeout()

    def test_clear_ok(self):
        """
        Exercise a normal clear command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        output = s3270.clear()
        self.assertEqual('L U U N N 4 24 80 0 0 0x0 -\nok\n', output)
    # test_clear_ok()

    def test_clear_error(self):
        """
        Exercise a clear command returning error

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to error
        self.mock_pipeconnector.return_value.run.return_value = [
            'error\n', 'L U U N N 4 24 80 0 0 0x0 -\nerror\n'
        ]
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(S3270StatusError, s3270.clear)
    # test_clear_error()

    def test_clear_timeout(self):
        """
        Exercise a clear command returning timeout

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to timeout
        self.mock_pipeconnector.return_value.run.side_effect = TimeoutError()

        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(TimeoutError, s3270.clear)
    # test_clear_timeout()

    def test_connect_ok(self):
        """
        Exercise a normal connect command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        output = s3270.connect('test.host.com')
        self.assertEqual('L U U N N 4 24 80 0 0 0x0 -\nok\n', output)
    # test_connect_ok()

    def test_connect_error(self):
        """
        Exercise a connect command returning error

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to error
        self.mock_pipeconnector.return_value.run.return_value = [
            'error\n', 'L U U N N 4 24 80 0 0 0x0 -\nerror\n'
        ]

        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(S3270StatusError, s3270.connect, 'test.host.com')
    # test_connect_error()

    def test_connect_first_timeout(self):
        """
        Exercise a connect command returning timeout

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to timeout
        self.mock_pipeconnector.return_value.run.side_effect = TimeoutError()

        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(TimeoutError, s3270.connect, 'test.host.com')
    # test_connect_first_timeout()

    def test_connect_second_timeout(self):
        """
        Exercise a connect command returning timeout

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to timeout
        self.mock_pipeconnector.return_value.run.return_value = ['', '']

        time_patcher = patch('time.time', autospec=True)
        mock_time = time_patcher.start()
        self.addCleanup(time_patcher.stop)

        mock_time.side_effect = [
            1475010078.6838996,
            1475010111.7996376,
            1475010511.7996376,
        ]

        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(TimeoutError, s3270.connect, 'test.host.com')
    # test_connect_second_timeout()

    def test_connect_second_timeout_wrong_status(self):
        """
        Exercise a connect command returning timeout

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to timeout
        self.mock_pipeconnector.return_value.run.side_effect = [
            ('break', ''),
            ('break', ''),
            ]

        time_patcher = patch('time.time', autospec=True)
        mock_time = time_patcher.start()
        self.addCleanup(time_patcher.stop)

        mock_time.side_effect = [
            1475010078.6838996,
            1475010111.7996376,
            1475010511.7996376,
        ]

        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(TimeoutError, s3270.connect, 'test.host.com')
    # test_connect_second_timeout_wrong_status()

    def test_connect_no_address(self):
        """
        Exercise a connect command returning error

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to error
        self.mock_pipeconnector.return_value.run.return_value = [
            'ok\n', 'No address associated with hostname\nok\n'
        ]

        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(S3270StatusError, s3270.connect, 'test.host.com')
    # test_connect_no_address()

    def test_disconnect_ok(self):
        """
        Exercise a normal disconnect command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        output = s3270.disconnect()
        self.assertEqual('L U U N N 4 24 80 0 0 0x0 -\nok\n', output)
    # test_ascii_ok()

    def test_disconnect_error(self):
        """
        Exercise a disconnect command returning error

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to error
        self.mock_pipeconnector.return_value.run.return_value = [
            'error\n', 'L U U N N 4 24 80 0 0 0x0 -\nerror\n'
        ]
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(S3270StatusError, s3270.disconnect)
    # test_disconnect_error()

    def test_disconnect_timeout(self):
        """
        Exercise a disconnect command returning timeout

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to timeout
        self.mock_pipeconnector.return_value.run.side_effect = TimeoutError()

        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(TimeoutError, s3270.disconnect)
    # test_disconnect_timeout()

    def test_enter_ok(self):
        """
        Exercise a normal enter command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        output = s3270.enter()
        self.assertEqual('L U U N N 4 24 80 0 0 0x0 -\nok\n', output)
    # test_enter_ok()

    def test_enter_error(self):
        """
        Exercise an enter command returning error

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to error
        self.mock_pipeconnector.return_value.run.return_value = [
            'error\n', 'L U U N N 4 24 80 0 0 0x0 -\nerror\n'
        ]
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(S3270StatusError, s3270.enter)
    # test_enter_error()

    def test_enter_timeout(self):
        """
        Exercise a enter command returning timeout

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to timeout
        self.mock_pipeconnector.return_value.run.side_effect = TimeoutError()

        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(TimeoutError, s3270.enter)
    # test_enter_timeout()

    def test_execute_ok(self):
        """
        Exercise a normal execute command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        output = s3270.execute('time')
        self.assertEqual('L U U N N 4 24 80 0 0 0x0 -\nok\n', output)
    # test_execute_ok()

    def test_execute_error(self):
        """
        Exercise an execute command returning error

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to error
        self.mock_pipeconnector.return_value.run.return_value = [
            'error\n', 'L U U N N 4 24 80 0 0 0x0 -\nerror\n'
        ]
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(S3270StatusError, s3270.execute, 'time')
    # test_execute_error()

    def test_execute_timeout(self):
        """
        Exercise a execute command returning timeout

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to timeout
        self.mock_pipeconnector.return_value.run.side_effect = TimeoutError()

        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(TimeoutError, s3270.execute, 'bash')
    # test_execute_timeout()

    def test_query_ok(self):
        """
        Exercise a normal query command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        output = s3270.query()
        self.assertEqual('L U U N N 4 24 80 0 0 0x0 -\nok\n', output)
    # test_query_ok()

    def test_query_attribute_ok(self):
        """
        Exercise a normal query command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        output = s3270.query('Host')
        self.assertEqual('L U U N N 4 24 80 0 0 0x0 -\nok\n', output)
    # test_query_attribute_ok()

    def test_query_error(self):
        """
        Exercise an query command returning error

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to error
        self.mock_pipeconnector.return_value.run.return_value = [
            'error\n', 'L U U N N 4 24 80 0 0 0x0 -\nerror\n'
        ]
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(S3270StatusError, s3270.query)
    # test_query_error()

    def test_query_timeout(self):
        """
        Exercise a query command returning timeout

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to timeout
        self.mock_pipeconnector.return_value.run.side_effect = TimeoutError()

        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(TimeoutError, s3270.query)
    # test_query_timeout()

    def test_query_attribute_timeout(self):
        """
        Exercise a query command returning timeout

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to timeout
        self.mock_pipeconnector.return_value.run.side_effect = TimeoutError()

        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(TimeoutError, s3270.query, 'Host')
    # test_query_attribute_timeout()

    def test_quit_ok(self):
        """
        Exercise a normal quit command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        s3270.quit()
        self.assertIsNone(s3270._s3270)
        self.assertIsNone(s3270.host_name)
    # test_quit_ok()

    def test_quit_timeout(self):
        """
        Exercise a quit command returning timeout

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to timeout
        self.mock_pipeconnector.return_value.quit.side_effect = TimeoutError()

        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(TimeoutError, s3270.quit)
    # test_quit_timeout()

    def test_snap_ok(self):
        """
        Exercise a normal snap command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        output = s3270.snap()
        self.assertEqual('L U U N N 4 24 80 0 0 0x0 -\nok\n', output)
    # test_snap_ok()

    def test_snap_attribute_ok(self):
        """
        Exercise a normal snap with attribute command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        output = s3270.snap('Rows')
        self.assertEqual('L U U N N 4 24 80 0 0 0x0 -\nok\n', output)
    # test_snap_attribute_ok()

    def test_snap_error(self):
        """
        Exercise an snap command returning error

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to error
        self.mock_pipeconnector.return_value.run.return_value = [
            'error\n', 'L U U N N 4 24 80 0 0 0x0 -\nerror\n'
        ]
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(S3270StatusError, s3270.snap)
    # test_snap_error()

    def test_snap_timeout(self):
        """
        Exercise a snap command returning timeout

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to timeout
        self.mock_pipeconnector.return_value.run.side_effect = TimeoutError()

        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(TimeoutError, s3270.snap)
    # test_snap_timeout()

    def test_snap_attribute_timeout(self):
        """
        Exercise a snap command returning timeout

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to timeout
        self.mock_pipeconnector.return_value.run.side_effect = TimeoutError()

        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(TimeoutError, s3270.snap, 'ascii')
    # test_snap_attribute_timeout()

    def test_string_ok(self):
        """
        Exercise a normal string command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        output = s3270.string('test')
        self.assertEqual('L U U N N 4 24 80 0 0 0x0 -\nok\n', output)
    # test_string_ok()

    def test_string_error(self):
        """
        Exercise a string command returning error

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to error
        self.mock_pipeconnector.return_value.run.return_value = [
            'error\n', 'L U U N N 4 24 80 0 0 0x0 -\nerror\n'
        ]
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(S3270StatusError, s3270.string, 'test')
    # test_string_error()

    def test_string_timeout(self):
        """
        Exercise a string command returning timeout

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to timeout
        self.mock_pipeconnector.return_value.run.side_effect = TimeoutError()

        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        self.assertRaises(TimeoutError, s3270.string, 'ascii')
    # test_string_timeout()

    def test_transfer_ok(self):
        """
        Exercise a normal transfer command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        mock_output = (
            'U U U C(hostname.com) I 4 24 80 0 0 0x0 0.008\n'
            'ok                                             \n'
        )
        self.mock_pipeconnector.return_value.run.return_value = (
            'ok', mock_output)

        # create new instance of s3270
        s3270 = S3270()

        args = ['/some/file', 'DEST FILE A']

        output = s3270.transfer(*args, timeout=10)
        self.assertEqual(output, mock_output)
        self.mock_pipeconnector.return_value.run.assert_called_with(
            'Transfer(Direction=send, "LocalFile={}", "HostFile={}", '
            'Mode=binary, Recfm=fixed, Host=vm)'.format(args[0], args[1]),
            timeout=10)
    # test_transfer_ok()

    def test_transfer_error(self):
        """
        Exercise a transfer command returning error

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to error
        mock_output = (
            "data: Local file '/some/file': No such file or directory    \n"
            "U F U C(hostname.com) I 4 43 80 41 0 0x0 -\n"
            "error                                          \n"
        )
        self.mock_pipeconnector.return_value.run.return_value = (
            "error", mock_output)

        # create new instance of s3270
        s3270 = S3270()

        # perform action
        args = ['/some/file', 'DEST FILE A']
        with self.assertRaisesRegex(
            S3270StatusError, 'Failed to execute Transfer command'):
            s3270.transfer(*args)
    # test_transfer_error()

    def test_transfer_extra_params(self):
        """
        Exercise a call to transfer using extra parameters
        """
        mock_output = (
            'U U U C(hostname.com) I 4 24 80 0 0 0x0 0.008\n'
            'ok                                             \n'
        )
        self.mock_pipeconnector.return_value.run.return_value = (
            'ok', mock_output)

        s3270 = S3270()

        # perform action
        kwargs = {
            'local_path': '/some/file',
            'remote_path': 'SRC FILE A',
            'direction': 'receive',
            'mode': 'ascii',
            'recfm': 'variable',
            'timeout': 100,
            'extra1': 'value1'
        }
        expected_args = (
            'Direction={direction}, "LocalFile={local_path}", '
            '"HostFile={remote_path}", Mode={mode}, Recfm={recfm}, '
            'Host=vm, extra1="value1"'.format(**kwargs))

        output = s3270.transfer(**kwargs)
        self.assertEqual(output, mock_output)
        self.mock_pipeconnector.return_value.run.assert_called_with(
            'Transfer({})'.format(expected_args), timeout=kwargs['timeout'])

    # test_transfer_extra_params()

    def test_transfer_invalid_value(self):
        """
        Exercise a wrong call to transfer by specifying invalid values
        """
        s3270 = S3270()

        # specify invalid direction's value
        kwargs = {
            'local_path': '/some/file',
            'remote_path': 'SRC FILE A',
            'direction': 'wrong_value',
        }
        with self.assertRaisesRegex(ValueError, 'Invalid direction'):
            s3270.transfer(**kwargs, timeout=10)

        # invalid mode
        kwargs.pop('direction')
        kwargs['mode'] = 'wrong_value'
        with self.assertRaisesRegex(ValueError, 'Invalid mode'):
            s3270.transfer(**kwargs, timeout=10)

        # invalid recfm
        kwargs.pop('mode')
        kwargs['recfm'] = 'wrong_value'
        with self.assertRaisesRegex(ValueError, 'Invalid recfm'):
            s3270.transfer(**kwargs, timeout=10)
    # test_transfer_invalid_value()

    def test_transfer_timeout(self):
        """
        Exercise a transfer command returning timeout

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set status to timeout
        self.mock_pipeconnector.return_value.run.side_effect = TimeoutError()

        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        with self.assertRaises(TimeoutError):
            s3270.transfer('/some/file', 'DEST FILE A')
    # test_string_timeout()
# TestS3270
