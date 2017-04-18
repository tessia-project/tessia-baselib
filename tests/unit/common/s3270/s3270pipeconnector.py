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
S3270PipeConnector unittest
"""
# pylint: disable=no-member,attribute-defined-outside-init,no-self-use,line-too-long
#
# IMPORTS
#
from unittest.mock import patch, Mock
from unittest import TestCase
from tessia_baselib.common.s3270.s3270pipeconnector import S3270PipeConnector
from subprocess import TimeoutExpired

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
class TestS3270PipeConnector(TestCase):
    """
    Unit test for the S3270PipeConnector class
    """

    def setUp(self):
        """
        Mock subprocess.Popen and select.poll

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        self.popen_patcher = patch('subprocess.Popen', autospec=True)
        self.mock_popen = self.popen_patcher.start()
        self.addCleanup(self.popen_patcher.stop)

        self.mock_rv = Mock()
        self.mock_rv.stdout.fileno.return_value = 5
        self.mock_rv.stdin.fileno.return_value = 4

        self.mock_popen.return_value = self.mock_rv

        self.poll_patcher = patch('select.epoll', autospec=True)
        self.mock_poll = self.poll_patcher.start()
        self.addCleanup(self.poll_patcher.stop)

        self.mock_poll.return_value.poll.side_effect = [
            [(4, 4)], [(5, 1)]
        ]

        self.read_patcher = patch(
            'tessia_baselib.common.s3270.s3270pipeconnector.read', autospec=True
        )
        self.mock_read = self.read_patcher.start()
        self.addCleanup(self.read_patcher.stop)

        self.mock_read.side_effect = [
            b'L U U N N 4 24 80 0 0 0x0 -\n', b'ok\n'
        ]
    # setUp()

    def tearDown(self):
        pass
    # tearDown()

    def test_run_commands(self):
        """
        Exercise a normal execution of a command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set poll to false so we have stdin not ready
        self.mock_poll.return_value.poll.side_effect = [
            [(4, 4)], [(5, 1)], [(5, 1)],
        ]

        # create new instance of s3270 connector using Pipes
        s3270_connector = S3270PipeConnector()

        # simple command execution
        status, output = s3270_connector.run('Clear')
        self.assertEqual('ok', status)
        self.assertEqual('L U U N N 4 24 80 0 0 0x0 -\nok\n', output)
    # test_run_commands()

    def test_run_commands_half_output(self):
        """
        Exercise a normal execution of a command reading partial output

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        self.mock_read.side_effect = [
            b'L U U N N 4 24 80 0 0 ', b'0x0 -\nok\n'
        ]

        # set poll to false so we have stdin not ready
        self.mock_poll.return_value.poll.side_effect = [
            [(4, 4)], [(5, 1)], [(5, 1)],
        ]

        # create new instance of s3270 connector using Pipes
        s3270_connector = S3270PipeConnector()

        # simple command execution
        status, output = s3270_connector.run('Clear')
        self.assertEqual('ok', status)
        self.assertEqual('L U U N N 4 24 80 0 0 0x0 -\nok\n', output)
    # test_run_commands_half_output()

    def test_quit_command(self):
        """
        Exercise a normal execution of a command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of s3270 connector using Pipes
        s3270_connector = S3270PipeConnector()

        # simple command execution
        s3270_connector.quit()
    # test_quit_command()

    def test_stdin_not_ready(self):
        """
        Exercise when stdin is not ready

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set poll to false so we have stdin not ready
        self.mock_poll.return_value.poll.side_effect = [
            [], [(5, 1)]
        ]

        self.time_patcher = patch('time.time', autospec=True)
        self.mock_time = self.time_patcher.start()
        self.addCleanup(self.time_patcher.stop)

        #self.mock_time_rv = Mock()
        self.mock_time.side_effect = [1475010078.6838996, 1475010211.7996376]

        # create new instance of s3270 connector using Pipes
        s3270_connector = S3270PipeConnector()

        # simple command execution
        self.assertRaises(TimeoutError, s3270_connector.run, "Clear")
    # test_stdin_not_ready()

    def test_read_external_timeout(self):
        """
        Exercise when stdout is not ready

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        self.mock_poll.return_value.poll.side_effect = [
            [(4, 4)], [],
        ]

        self.time_patcher = patch('time.time', autospec=True)
        self.mock_time = self.time_patcher.start()
        self.addCleanup(self.time_patcher.stop)

        #self.mock_time_rv = Mock()
        self.mock_time.side_effect = [
            1475010078.6838996,
            1475010111.7996376,
            1475010078.6838996,
            1475010211.7996376,
        ]

        # create new instance of s3270 connector using Pipes
        s3270_connector = S3270PipeConnector()

        # simple command execution
        self.assertRaises(TimeoutError, s3270_connector.run, "Clear")
    # test_read_external_timeout()

    def test_read_internal_timeout(self):
        """
        Exercise when stdout is not ready

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        self.mock_poll.return_value.poll.side_effect = [
            [(4, 4)], [(0, 0)],
        ]

        self.time_patcher = patch('time.time', autospec=True)
        self.mock_time = self.time_patcher.start()
        self.addCleanup(self.time_patcher.stop)

        #self.mock_time_rv = Mock()
        self.mock_time.side_effect = [
            1475010078.6838996,
            1475010111.7996376,
            1475010078.6838996,
            1475010211.7996376,
        ]

        # create new instance of s3270 connector using Pipes
        s3270_connector = S3270PipeConnector()

        # simple command execution
        self.assertRaises(TimeoutError, s3270_connector.run, "Clear")
    # test_read_internal_timeout()

    def test_command_read_timeout(self):
        """
        Exercise when stdout has not sent all the output

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        self.time_patcher = patch('time.time', autospec=True)
        self.mock_time = self.time_patcher.start()
        self.addCleanup(self.time_patcher.stop)

        #self.mock_time_rv = Mock()
        self.mock_time.side_effect = [1475010078.6838996, 1475010211.7996376]

        # create new instance of s3270 connector using Pipes
        s3270_connector = S3270PipeConnector()

        # simple command execution
        self.assertRaises(TimeoutError, s3270_connector.run, "Clear")
    # test_command_read_timeout()

    def test_terminate_command(self):
        """
        Exercise a normal execution of a command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of s3270 connector using Pipes
        s3270_connector = S3270PipeConnector()

        # simple command execution
        s3270_connector.terminate()
    # test_terminate_command()

    def test_terminate_timeout_command(self):
        """
        Exercise a normal execution of a command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """

        self.mock_communicate = Mock()
        self.mock_communicate.communicate.side_effect = TimeoutExpired("cmd", 60)

        self.mock_popen.return_value = self.mock_communicate

        # create new instance of s3270 connector using Pipes
        s3270_connector = S3270PipeConnector()

        # simple command execution
        self.assertRaises(
            TimeoutExpired,
            s3270_connector.terminate,
            "timeout=60"
        )
    # test_terminate_timeout_command()

# TestS3270PipeConnector
