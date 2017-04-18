# Copyright 2017 IBM Corp.
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
Test module for zvm hypervisor
"""

#
# IMPORTS
#
from tessia_baselib.hypervisors.zvm.zvm import HypervisorZvm
from unittest import TestCase
from unittest.mock import patch

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
class TestHypervisorZvm(TestCase):
    """
    Unit test for the HypervisorZvm class
    """

    def setUp(self):
        """
        Mock Terminal

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        self.terminal_patcher = patch(
            'tessia_baselib.hypervisors.zvm.zvm.Terminal',
            autospec=True)
        self._mock_terminal = self.terminal_patcher.start()
        self.addCleanup(self.terminal_patcher.stop)

        # set s3270 output
        self._mock_terminal.return_value.login.return_value = 'ok\n'
    # setUp()

    def test_login_ok(self):
        """
        Exercise a normal login command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of terminal
        hyp = HypervisorZvm(
            "hostname",
            "hostname.com",
            "user",
            "password",
            None
        )

        # simple command execution
        hyp.login()
        self._mock_terminal.return_value.login.assert_called_once_with(
            "hostname.com",
            "user",
            "password",
            {},
            60
        )
    # test_login_ok()

    def test_logoff_ok(self):
        """
        Exercise a normal logoff command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of terminal
        hyp = HypervisorZvm(
            "hostname",
            "hostname.com",
            "user",
            "password",
            None
        )

        # simple command execution
        hyp.login()
        hyp.logoff()
        self._mock_terminal.return_value.disconnect.assert_called_once_with()
    # test_logoff_ok()

    def test_logoff_failed(self):
        """
        Exercise a failed logoff command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        self._mock_terminal.return_value.disconnect.return_value = False
        # create new instance of terminal
        hyp = HypervisorZvm(
            "hostname",
            "hostname.com",
            "user",
            "password",
            None
        )

        # simple command execution
        hyp.login()
        self.assertRaises(RuntimeError, hyp.logoff)
    # test_logoff_failed()

    def test_start_ok(self):
        """
        Exercise a normal start command

        *** Placeholder for start test when implemented ***

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of terminal
        hyp = HypervisorZvm(
            "hostname",
            "hostname.com",
            "user",
            "password",
            None
        )

        # simple command execution
        hyp.login()
        self.assertRaises(NotImplementedError, hyp.start,
                          "hostname", "cpu", "memory", None)
    # test_start_ok()

    def test_stop_ok(self):
        """
        Exercise a normal stop command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of terminal
        hyp = HypervisorZvm(
            "hostname",
            "hostname.com",
            "user",
            "password",
            None
        )

        # simple command execution
        hyp.login()
        hyp.stop("hostname", None)
        self._mock_terminal.return_value.logoff.assert_called_once_with()
    # test_stop_ok()

    def test_stop_failed(self):
        """
        Exercise a failed stop command

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        self._mock_terminal.return_value.logoff.return_value = False
        # create new instance of terminal
        hyp = HypervisorZvm(
            "hostname",
            "hostname.com",
            "user",
            "password",
            None
        )

        # simple command execution
        hyp.login()
        self.assertRaises(RuntimeError, hyp.stop,
                          "hostname", None)
    # test_stop_failed()

    def test_reboot_ok(self):
        """
        Exercise a normal reboot command

        *** Placeholder for reboot test when implemented ***

        Args:
            None

        Raises:
            AssertionError: if the session object does not behave as expected
        """
        # create new instance of terminal
        hyp = HypervisorZvm(
            "hostname",
            "hostname.com",
            "user",
            "password",
            None
        )

        # simple command execution
        hyp.login()
        self.assertRaises(NotImplementedError, hyp.reboot,
                          "hostname", None)
    # test_reboot_ok()

# TestHypervisorZvm
