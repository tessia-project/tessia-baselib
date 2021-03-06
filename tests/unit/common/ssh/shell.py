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
Defines a TestCase class for unit tests for the ssh
shell class.
"""

#
# IMPORTS
#

from tessia.baselib.common.ssh import shell as shell_module
from tessia.baselib.common.ssh.exceptions import SshShellError
from unittest import main as unittest_main
from unittest import mock
from unittest import TestCase
from uuid import uuid4

import itertools
import paramiko
import socket

#
# CONSTANTS AND DEFINITIONS
#


#
# CODE
#
class TestSshShell(TestCase):
    """
    Test class for SshShell class.
    """
    ENCODING = 'utf-8'
    STATUS_COMMAND = 'echo $?'

    def _build_regular_run_output(self, cmd, output, status=0):
        '''
        Return output for mocked recv function.

        Construct output that the run() function of the shell
        will expect under normal conditions. The run() function
        calls _read() three times, one for reading any garbage left,
        one for reading the real output of the command, and one for
        reading the output of 'echo $?' to know the exist status of the
        command.

        The return value can be set as the side_effect of a mocked recv
        function of the shell's channel so that it's return value iterates
        through these three outputs every time it is called through _read().

        Args:
            cmd (str): command that will be sent to run()
            output (str): output to return after the command echo
            status (int): status that should be returned by echo $?

        Returns:
            list: expected channel outputs after run() is called

        Raises:
        '''

        return [self._make_output('', 'garbage'),
                self._make_output(cmd, output),
                self._make_output(self.STATUS_COMMAND, str(status))]

    def _create_regular_shell(self):
        '''
        Construct a shell object with no errors.

        Args:
            None

        Returns:
            SshShell: object

        Raises:
            None
        '''
        # set output of recv so that the first call to _read
        # and the call to run 'locale charmap' in the SshShell constructor work
        self._dummy_socket.recv.side_effect = (
            [self._make_output('', '\n')]
            + [self._make_output('', 'output')]
            + self._build_regular_run_output(
                'export SYSTEMD_PAGER=; export LC_ALL=en_US.UTF-8; '
                'locale charmap', 'UTF-8')
        )

        shell = shell_module.SshShell(self._dummy_socket)

        # Reset the side effect so it won't affect other parts
        # of the test.
        self._dummy_socket.recv.side_effect = None

        return shell

    def _make_output(self, cmd_echo, output):
        '''
        Construct output for mocked recv function.

        Args:
            cmd_echo (str): command echo to prepend to the output
            output (str): output to return after the command echo

        Returns:
            str: Output formed by appending the command echo, CRLF, the
                 specified output, CRLF and the prompt

        Raises:
        '''
        return (
            '{}\r\n{}\r\n{}'.format(
                cmd_echo,
                output,
                self._prompt)).encode(self.ENCODING)

    def setUp(self):
        """
        Create the shell object and replaces common objects by mocks.

        Args:
        Returns:
        Raises:
        """

        # Replace uuid4 function used by the shell module
        # by a mock that will return a fixed uuid, so that
        # we can set our mock socket to use the same uuid
        # when printing the prompt, since the mock socket
        # won't actually execute 'export PS1=...'
        uid = str(uuid4())

        shell_module.uuid4 = mock.MagicMock(return_value=uid)

        self._prompt = uid + ':'

        self._dummy_socket = mock.MagicMock(spec_set=paramiko.channel.Channel)

        # Mock the select function used by the shell module to
        # always return the socket as ready to be read from.
        shell_module.select = mock.MagicMock()

        shell_module.select.select.return_value = [self._dummy_socket], [], []

        # In most cases, we want the send function to report that
        # it was able to send all of the bytes.
        self._dummy_socket.send.side_effect = len

        self._shell = self._create_regular_shell()

    def tearDown(self):
        '''
        Reset select function mock so next tests don't break.

        Args:
        Returns:
        Raises:
        '''
        shell_module.select.select.side_effect = None

        for call in self._dummy_socket.send.call_args_list:
            # Check that if send was called, it was called with a single
            # bytes argument.
            # The call object in call_args_list is a tuple (args, kwargs)
            # and we expect args to have a single element. We expectd this
            # element to have been called with a bytes object. Even
            # though the paramiko channel send function can also
            # implicitly encode strings into bytes, we should have
            # encoded any string ourselves so that we correctly
            # check the number of bytes sent in the _write function.
            self.assertEqual(len(call[0]), 1)
            self.assertIsInstance(call[0][0], bytes)

        # pylint: disable=no-member
        shell_module.select.select.reset_mock()

    def test_close(self):
        """
        Test that a call to close() on the shell object will
        call close() on the ssh channel.

        Args:
        Returns:
        Raises:
        """

        self._shell.close()

        self.assertEqual(self._shell.socket.close.call_count,
                         1)

    def test_close_exception(self):
        """
        Test that a call to close() will work even if the underlying socket
        raises an exception.
        """
        self._shell.socket.close.side_effect = Exception()
        self._shell.close()

        self.assertEqual(self._shell.socket.close.call_count, 1)
    # test_close_exception()

    def test_run(self):
        """
        Test regular run function.

        Args:
        Returns:
        Raises:
        """

        cmd = 'dummy_cmd'
        expected_output = 'dummy_output'
        self._shell.socket.recv.side_effect = (
            self._build_regular_run_output(cmd, expected_output))

        status, output = self._shell.run(cmd + '\n')

        self.assertIsInstance(status, int)
        self.assertEqual(output, expected_output + '\n')

    def test_run_no_return(self):
        """
        Test regular run function with the return flag set.

        Args:
        Returns:
        Raises:
        """

        cmd = 'dummy_cmd'
        expected_output = 'dummy_output'
        self._shell.socket.recv.side_effect = (
            self._build_regular_run_output(cmd, expected_output))

        status, output = self._shell.run(cmd + '\n', ignore_ret=True)

        self.assertEqual(status, 0)
        self.assertEqual(output, "")
    # test_run_no_return()

    def test_run_bad_status(self):
        """
        Test a call to run that fails when casting
        the return status to an int.

        Args:
        Returns:
        Raises:
        """

        # The third element will be returned by the third
        # call to _read() when the shell tries to read the
        # exit code.
        self._shell.socket.recv.side_effect = [
            self._make_output('', 'garbage'),
            self._make_output('dummy_cmd', 'output'),
            self._make_output(self.STATUS_COMMAND, 'not-an-int')
        ]

        with self.assertRaises(SshShellError):
            self._shell.run('dummy_cmd')

    def test_run_chunked_read(self):
        """
        Test call to run() where the underlying call
        to _read takes more than a single call to recv()
        to read the whole output expected output.

        Args:
        Returns:
        Raises:
        """
        cmd = 'dummy_cmd'
        expected_output = 'dummy_output'

        # Separate output\r\nprompt so that it
        # is returned in three separate parts by recv.
        recv_output = [
            self._make_output('', 'garbage'),
            expected_output.encode(self.ENCODING),
            '\r\n'.encode(self.ENCODING),
            self._prompt.encode(self.ENCODING),
            self._make_output(self.STATUS_COMMAND, '0')
        ]

        self._shell.socket.recv.side_effect = recv_output

        self._shell.socket.recv.reset_mock()

        status, output = self._shell.run(cmd)

        self.assertIsInstance(status, int)
        self.assertEqual(output, expected_output + '\n')

        self.assertEqual(self._shell.socket.recv.call_count,
                         len(recv_output))

    def test_run_distorted_unicode(self):
        """
        Test that unicode character received in different buffers will be
        correctly processed.

        Args:
        Returns:
        Raises:
        """

        # The correct unicode character was received in different buffers.
        expected_output = "Cyrillic 'а' is valid"
        recv_output = [
            self._make_output('', 'garbage'),
            "Cyrillic '".encode(self.ENCODING) +
            b'\xd0',
            b'\xb0' +
            "' is valid\r\n".encode(self.ENCODING),
            self._prompt.encode(self.ENCODING),
            self._make_output(self.STATUS_COMMAND, '0')
        ]

        self._shell.socket.recv.side_effect = recv_output
        self._shell.socket.recv.reset_mock()

        status, output = self._shell.run('dummy_cmd')
        self.assertEqual(status, 0)
        self.assertEqual(output, expected_output + '\n')

        # The non valid single-byte unicode character was received.
        recv_output = [
            'Cyrillic '.encode(self.ENCODING),
            b'\xd0',
            ' is not valid'.encode(self.ENCODING),
            self._prompt.encode(self.ENCODING),
            self._make_output(self.STATUS_COMMAND, '0')
        ]

        self._shell.socket.recv.side_effect = recv_output
        self._shell.socket.recv.reset_mock()

        with self.assertRaises(SshShellError):
            self._shell.run('dummy_cmd')

        # The non valid compound unicode character was received.
        recv_output = [
            'Cyrillic '.encode(self.ENCODING),
            b'\xd0',
            b'\xd0',
            b'\xd0',
            b'\xd0',
            ' is not valid'.encode(self.ENCODING),
            self._prompt.encode(self.ENCODING),
            self._make_output(self.STATUS_COMMAND, '0')
        ]

        self._shell.socket.recv.side_effect = recv_output
        self._shell.socket.recv.reset_mock()

        with self.assertRaises(SshShellError):
            self._shell.run('dummy_cmd')
    # test_run_distorted_unicode()

    def test_run_chunked_write(self):
        """
        Test a call to run() that has to call
        send on the channel multiple times.

        Args:
        Returns:
        Raises:
        """

        cmd = 'dummy_cmd'
        expected_output = 'dummy_output'
        self._shell.socket.recv.side_effect = (
            self._build_regular_run_output(cmd, expected_output))

        # clear side effect so that return value
        # is used isntead
        self._shell.socket.send.side_effect = None

        # report one byte sent at a time
        self._shell.socket.send.return_value = 1

        # Send was already used by the constructor, so reset it
        # here so we have a predictable call count.
        self._shell.socket.send.reset_mock()

        # Wrap _write in a magic mock so we can count the
        # bytes that run() tries to send.
        self._shell._write = mock.MagicMock(side_effect=self._shell._write)

        cmd = 'dummy_cmd\n'
        status, output = self._shell.run(cmd)

        # Check if run worked, like before.
        self.assertIsInstance(status, int)
        self.assertEqual(output, expected_output + '\n')

        # Find out which arguments were used to call _write() when
        # run() was called.
        write_arguments = [
            call[0][0]  # first arg of the positional args of _write()
            for call in self._shell._write.call_args_list
        ]

        expected_send_call_count = 0

        # Compute number of bytes passed to _write, and by
        # extension, the expected number of calls to send,
        # since we forced it to return a single byte sent at
        # a time.
        for content in write_arguments:
            expected_send_call_count += len(content)

        self.assertEqual(self._shell.socket.send.call_count,
                         expected_send_call_count)

    def test_run_escape_chars(self):
        """
        Test a call to run when it receives character escape sequences
        in the echo of the command.
        """
        expected_output = 'dummy_output'
        self._shell.socket.recv.side_effect = (
            self._make_output('', 'garbage'),
            self._make_output('dummy_cmd', 'dummy_output'),
            self._make_output('\x1b[6n{}'.format(self.STATUS_COMMAND), 0))

        status, output = self._shell.run('dummy_cmd')

        self.assertIsInstance(status, int)
        self.assertEqual(output, expected_output + '\n')

    def test_run_no_newline(self):
        """
        Test a call to run that has to append
        a newline to the command.

        Args:
        Returns:
        Raises:
        """

        cmd = 'dummy_cmd'
        expected_output = 'dummy_output'
        self._shell.socket.recv.side_effect = (
            self._build_regular_run_output(cmd, expected_output))

        status, output = self._shell.run('dummy_cmd')

        self.assertIsInstance(status, int)
        self.assertEqual(output, expected_output + '\n')

    def test_run_read_slow_select(self):
        """
        Test call to run() where the underlying call
        to _read takes more than a single call to select()
        before being able to read from the channel.

        Args:
        Returns:
        Raises:
        """
        cmd = 'dummy_cmd'
        expected_output = 'dummy_output'
        self._shell.socket.recv.side_effect = (
            self._build_regular_run_output(cmd, expected_output))

        # Mock select so that it will report no handles
        # ready to be read from on the first call, and
        # the channel as ready to be read from on the second call.
        shell_module.select.select.side_effect = itertools.cycle(
            [
                ([], [], []),
                ([self._shell.socket], [], []),
            ]
        )

        # pylint: disable=no-member
        shell_module.select.select.reset_mock()
        # pylint: enable=no-member

        # Wrap _read() in a magic mock so we can count how many times it
        # was called.
        self._shell._read = mock.MagicMock(side_effect=self._shell._read)

        status, output = self._shell.run('dummy_cmd\n')

        self.assertIsInstance(status, int)
        self.assertEqual(output, expected_output + '\n')

        # We exepct each read in run to have called select twice.
        expected_select_call_count = self._shell._read.call_count * 2
        # pylint: disable=no-member
        self.assertEqual(shell_module.select.select.call_count,
                         expected_select_call_count)

    def test_run_read_socket_timeout(self):
        '''
        Test that a call to recv on the channel will
        be properly logged as a warning by the shell.

        Args:
        Returns:
        Raises:
        '''

        cmd = 'dummy_cmd'
        expected_output = 'dummy_output'
        self._shell.socket.recv.side_effect = [
            socket.timeout,
            self._make_output('', 'garbage'),
            self._make_output(cmd, expected_output),
            self._make_output(self.STATUS_COMMAND, '0')]

        # Wrap the logger warning function in a magic mock
        # so we can check if it was called.
        self._shell._main_logger.warning = mock.MagicMock(
            side_effect=self._shell._main_logger.warning)

        status, output = self._shell.run(cmd)

        self.assertIsInstance(status, int)
        self.assertEqual(output, expected_output + '\n')
        self.assertTrue(self._shell._main_logger.warning.called)

    def test_run_read_timeout(self):
        '''
        Test a call do run() where the underlying
        call to _read() times out.

        Args:
        Returns:
        Raises:
        '''

        # Always return an emtpy string so that the shell
        # never reads the prompt in _read() and times out.
        self._shell.socket.recv.return_value = b''

        with self.assertRaises(TimeoutError):
            self._shell.run('dummy_cmd', timeout=0.001)

    def test_run_write_slow_send_ready(self):
        """
        Test a call to run() where send_ready takes two
        calls to report that the channel can be written to.

        Args:
        Returns:
        Raises:
        """
        cmd = 'dummy_cmd'
        expected_output = 'dummy_output'
        self._shell.socket.recv.side_effect = (
            self._build_regular_run_output(cmd, expected_output))

        # Make it so every call to _write() will take two calls
        # to send_ready() before calling send(). The cycle is so
        # that _write() can be called multiple times.
        self._shell.socket.send_ready.side_effect = (
            itertools.cycle([False, True])
        )

        # Reset send ready call counts, since it was used by the
        # shell constructor before.
        self._shell.socket.send_ready.reset_mock()

        self._shell._write = mock.MagicMock(side_effect=self._shell._write)

        status, output = self._shell.run('dummy_cmd\n')

        # Check if run worked, like before.
        self.assertIsInstance(status, int)
        self.assertEqual(output, expected_output + '\n')

        # We expect send_ready to be called twice for each time _write()
        # is called.
        expected_send_ready_call_count = self._shell._write.call_count * 2
        self.assertEqual(self._shell.socket.send_ready.call_count,
                         expected_send_ready_call_count)

    def test_run_write_timeout(self):
        """
        Test call to run() where the underlying call
        to _write() times out.

        Args:
        Returns:
        Raises:
        """
        cmd = 'dummy_cmd'
        expected_output = 'dummy_output'
        self._shell.socket.recv.side_effect = (
            self._build_regular_run_output(cmd, expected_output))

        self._shell.socket.send_ready.return_value = False

        original_write = shell_module.SshShell._write

        def partial_write(self, content):
            """
            Partial application of _write with a timeout
            set to a low value.
            """
            original_write(self, content, 0.01)

        # Substitute the _write() function in the shell so that the timeout
        # argument is set to a smaller value, since it cannot be set through
        # the call to run. We don't want to directly call _write() to test this
        # to ensure our test is done through a public interface.
        with mock.patch.object(shell_module.SshShell, '_write', partial_write):
            with self.assertRaises(TimeoutError):
                self._shell.run('dummy_cmd\n', timeout=0.1)

    def test_open_bad_charmap(self):
        """
        Test constructing shell object with an unexpected charmap.
        """
        obj_path = 'tessia.baselib.common.ssh.shell.get_logger'
        with mock.patch(obj_path) as get_logger_mock:

            bad_charmap = 'UTF-9'

            self._dummy_socket.recv.side_effect = (
                [self._make_output('', '\n')]
                + [self._make_output('', 'output')]
                + self._build_regular_run_output(
                    'export SYSTEMD_PAGER=; export LC_ALL=en_US.UTF-8; '
                    'locale charmap', bad_charmap)
            )

            shell_module.SshShell(self._dummy_socket)

            self.assertEqual(get_logger_mock.return_value.warning.call_count,
                             2)

            # The first warning call is specific to this error,
            # the second one is the same for both the locale call returning
            # a bad status and the charmap being unexpected.
            first_warning_call = (get_logger_mock.return_value.warning
                                  .call_args_list[0])

            expected_first_warning_call = mock.call(
                'Charmap file %s is not UTF-8',
                bad_charmap)

            self.assertEqual(first_warning_call,
                             expected_first_warning_call)

    def test_open_bad_locale_call(self):
        """
        Test constructing a shell object with a failed 'locale' call.
        """
        obj_path = 'tessia.baselib.common.ssh.shell.get_logger'
        with mock.patch(obj_path) as get_logger_mock:
            self._dummy_socket.recv.side_effect = (
                [self._make_output('', '\n')]
                + [self._make_output('', 'output')]
                + self._build_regular_run_output(
                    'export SYSTEMD_PAGER=; export LC_ALL=en_US.UTF-8; '
                    'locale charmap', 'UTF-8', 1)
            )

            shell_module.SshShell(self._dummy_socket)

            self.assertEqual(get_logger_mock.return_value.warning.call_count,
                             2)

            # The first warning call is specific to this error,
            # the second one is the same for both the locale call returning
            # a bad status and the charmap being unexpected.
            first_warning_call = (get_logger_mock.return_value.warning
                                  .call_args_list[0])

            expected_first_warning_call = mock.call(
                'Could not determine charmap')

            self.assertEqual(first_warning_call,
                             expected_first_warning_call)

if __name__ == '__main__':
    unittest_main()
