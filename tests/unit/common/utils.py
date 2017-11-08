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
Module for the TestUtils class.
"""

#
# IMPORTS
#
from tessia.baselib.common.utils import timer
from tessia.baselib.common.ssh.shell import SshShell
from unittest import mock

import unittest

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

class TestUtils(unittest.TestCase):
    """
    Class for tests of the utils module.
    """
    @mock.patch("tessia.baselib.common.utils.sleep", spec_set=True)
    def test_timer(self, mock_sleep):
        """
        Test the timer function for the general case. It succeeds
        after 3 trials.
        """
        mock_cmd_channel = mock.Mock(spec=SshShell)
        cmd = "some cmd"
        times = [1, 2, 3, 4]
        msg = "some msg"
        mock_cmd_channel.run.side_effect = [(1, ""), (1, ""),
                                            (0, ""), (0, "")]
        timer(mock_cmd_channel, cmd, times, msg)
        self.assertEqual(mock_sleep.mock_calls, [mock.call(1),
                                                 mock.call(2),
                                                 mock.call(3)])
    # test_timer()

    @mock.patch("tessia.baselib.common.utils.sleep", spec_set=True)
    def test_timer_fails(self, mock_sleep):
        """
        Test the timer function for the case that it should fail, after
        exceeding the 4 attempts.
        """
        mock_cmd_channel = mock.Mock(spec=SshShell)
        cmd = "some cmd"
        times = [1, 2, 3, 4]
        msg = "some msg"
        mock_cmd_channel.run.side_effect = [(1, ""), (1, ""),
                                            (1, ""), (1, "")]
        self.assertRaisesRegex(RuntimeError, msg, timer, mock_cmd_channel,
                               cmd, times, msg)

        self.assertEqual(mock_sleep.mock_calls, [mock.call(1),
                                                 mock.call(2),
                                                 mock.call(3),
                                                 mock.call(4)])
    # test_timer_fails()
# TestUtils
