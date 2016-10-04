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
# pylint: disable=no-member,too-many-public-methods,protected-access
#
# IMPORTS
#
from unittest.mock import patch
from unittest import TestCase
from tessia_baselib.common.s3270.s3270 import S3270
from tessia_baselib.common.s3270.exceptions import S3270StatusError
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

        Returns:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        self.pipeconnector_patcher = patch(
            'tessia_baselib.common.s3270.s3270.S3270PipeConnector',
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

        Returns:
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

    def test_ascii_error(self):
        """
        Exercise an ascii command returning error

        Args:
            None

        Returns:
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

    def test_clear_ok(self):
        """
        Exercise a normal clear command

        Args:
            None

        Returns:
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

        Returns:
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

        Returns:
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

    def test_disconnect_ok(self):
        """
        Exercise a normal disconnect command

        Args:
            None

        Returns:
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

        Returns:
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

    def test_enter_ok(self):
        """
        Exercise a normal enter command

        Args:
            None

        Returns:
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

        Returns:
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

    def test_execute_ok(self):
        """
        Exercise a normal execute command

        Args:
            None

        Returns:
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

        Returns:
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

    def test_query_ok(self):
        """
        Exercise a normal query command

        Args:
            None

        Returns:
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

        Returns:
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

        Returns:
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

    def test_quit_ok(self):
        """
        Exercise a normal quit command

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        s3270.quit()
        self.assertIsNone(s3270._s3270)
    # test_quit_ok()

    def test_snap_ok(self):
        """
        Exercise a normal snap command

        Args:
            None

        Returns:
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

        Returns:
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

        Returns:
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

    def test_string_ok(self):
        """
        Exercise a normal string command

        Args:
            None

        Returns:
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

        Returns:
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

    def test_transfer_ok(self):
        """
        Exercise a normal transfer command

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of s3270
        s3270 = S3270()

        # simple command execution
        output = s3270.transfer()
        self.assertEqual('L U U N N 4 24 80 0 0 0x0 -\nok\n', output)
    # test_transfer_ok()

    def test_transfer_error(self):
        """
        Exercise a transfer command returning error

        Args:
            None

        Returns:
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
        self.assertRaises(S3270StatusError, s3270.transfer)
    # test_transfer_error()


# TestS3270
