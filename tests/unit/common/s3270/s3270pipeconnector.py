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
# pylint: disable=no-member,attribute-defined-outside-init
#
# IMPORTS
#
from unittest.mock import patch, Mock
from unittest import TestCase
from tessia_baselib.common.s3270.s3270pipeconnector import S3270PipeConnector

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

        Returns:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        self.popen_patcher = patch('subprocess.Popen', autospec=True)
        self.mock_popen = self.popen_patcher.start()
        self.addCleanup(self.popen_patcher.stop)

        self.mock_rv = Mock()
        self.mock_rv.stdout.readline.side_effect = [
            "L U U N N 4 24 80 0 0 0x0 -\n", "ok\n"
        ]
        self.mock_popen.return_value = self.mock_rv

        self.poll_patcher = patch('select.poll', autospec=True)
        self.mock_poll = self.poll_patcher.start()
        self.addCleanup(self.poll_patcher.stop)

        #self.mock_pool = Mock()
        self.mock_poll.return_value.poll.return_value = True
    # setUp()

    def tearDown(self):
        #self.popen_patcher.stop()
        #self.poll_patcher.stop()
        pass
    # tearDown()

    def test_normal_commands(self):
        """
        Exercise a normal execution of a command

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of s3270 connector using Pipes
        s3270_connector = S3270PipeConnector()

        # simple command execution
        status, output = s3270_connector.run('Clear')
        self.assertEqual('ok', status)
        self.assertEqual('L U U N N 4 24 80 0 0 0x0 -\nok\n', output)
    # test_normal_commands()

    def test_stdin_not_ready(self):
        """
        Exercise when stdin is not ready

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # set poll to false so we have stdin not ready
        self.mock_poll.return_value.poll.return_value = False

        # create new instance of s3270 connector using Pipes
        s3270_connector = S3270PipeConnector()

        # simple command execution
        self.assertRaises(TimeoutError, s3270_connector.run, "Clear")
    # test_stdin_not_ready()

    def test_stdout_not_ready(self):
        """
        Exercise when stdout is not ready

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        self.mock_poll.return_value.poll.side_effect = [True, False]

        # create new instance of s3270 connector using Pipes
        s3270_connector = S3270PipeConnector()

        # simple command execution
        self.assertRaises(TimeoutError, s3270_connector.run, "Clear")
    # test_stdout_not_ready()

    def test_command_read_timeout(self):
        """
        Exercise when stdout has not sent all the output

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        self.time_patcher = patch('time.time', autospec=True)
        self.mock_time = self.time_patcher.start()
        self.addCleanup(self.time_patcher.stop)

        #self.mock_time_rv = Mock()
        self.mock_time.side_effect = [1475010078.6838996, 1475010211.7996376]
        #self.mock_time.return_value.time.return_value = self.mock_time_rv

        # create new instance of s3270 connector using Pipes
        s3270_connector = S3270PipeConnector()

        # simple command execution
        self.assertRaises(TimeoutError, s3270_connector.run, "Clear")
    # test_command_read_timeout()

# TestS3270PipeConnector
