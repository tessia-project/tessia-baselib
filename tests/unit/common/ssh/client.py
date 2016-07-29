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
Defines two TestCase classes for unit tests for the ssh
client class.
"""
# Since this is a test class, we need to access some
# protected members and we access some members in mocks
# that would cause 'no-member' warnings to be issued.
# pylint: disable=protected-access
# pylint: disable=no-member
#
# IMPORTS
#

from tessia_baselib.common.ssh import client
from tessia_baselib.common.ssh import shell as shell_module
from tessia_baselib.common.ssh.exceptions import SshClientError
from unittest import mock

import io
import paramiko
import logging
import stat
import unittest
import urllib

#
# CONSTANTS AND DEFINITIONS
#
HOST_NAME = 'localhost'
PORT = 1234
PASSWORD = 'password'
USERNAME = 'some_user'


#
# CODE
#

class TestSshClientConnected(unittest.TestCase):
    """
    Test class for the SshClient class.

    This class only tests methods that require the client to have
    called login.
    """

    def setUp(self):
        """
        Setup function called before every test_* function.

        Patch the paramiko SSHClient with a mock.

        The login method is called in setUp.

        Args:
            None

        Returns:
            None

        Raises:
            None
        """
        # Create a patcher to replace the paramiko SSHClient
        # class with a mock, this way no actual connection to
        # a real ssh server is needed.
        patcher = mock.patch(
            target='tessia_baselib.common.ssh.client.paramiko.SSHClient',
            autospec=True)

        # activate the patch
        self._mocked_paramiko_client = patcher.start()
        # ensure patch is reverted even if setUp throws an exception
        self.addCleanup(patcher.stop)

        # patch the function that gets a logger so that the test does not try
        # to create real log file on the filesystem
        log_patcher = mock.patch(
            'tessia_baselib.common.ssh.client.getLogger', autospec=True)
        log_patcher.start()
        # ensure patch is reverted even if setUp throws an exception
        self.addCleanup(log_patcher.stop)

        self._client = client.SshClient()

        # use 'wraps' so that the original method from the unit being tested is
        # used and we can still evaluate whether or not it was called.
        self._client._assert_connected = mock.MagicMock(
            wraps=self._client._assert_connected)

        # Create mocks for file descriptors returned by the
        # sftp open functions.
        mocked_sftp_read_fd = mock.MagicMock(spec_set=paramiko.SFTPFile)

        (mocked_sftp_read_fd.__enter__
         .return_value) = mock.MagicMock(spec_set=paramiko.SFTPFile)

        self._mocked_sftp_read_fd = (mocked_sftp_read_fd.__enter__
                                     .return_value)

        mocked_sftp_write_fd = mock.MagicMock()

        (mocked_sftp_write_fd.__enter__
         .return_value) = mock.MagicMock(spec_set=paramiko.SFTPFile)

        self._mocked_sftp_write_fd = (mocked_sftp_write_fd.__enter__
                                      .return_value)

        def mocked_sftp_open(*args):
            """
            A function to return the correct file descriptor
            mock depending on which mode is passed to the
            sftp open function.
            """
            mode = args[1]
            if mode == 'rb':
                return mocked_sftp_read_fd
            elif mode == 'wb' or mode == 'ab':
                return mocked_sftp_write_fd
            else:
                raise ValueError


        self._mocked_sftp_open = (self._mocked_paramiko_client.return_value
                                  .open_sftp.return_value
                                  .open)

        # Set the sftp open function to the one defined above.
        self._mocked_sftp_open.side_effect = mocked_sftp_open

        self._client.login(host_name=HOST_NAME, port=PORT,
                           user=USERNAME, passwd=PASSWORD)

    def tearDown(self):
        """
        Function called after every test_* function.

        Check if the tested method(s) checked that the client was
        logged in at least once.
        """
        self._client._assert_connected.assert_any_call()

    @mock.patch('urllib.request', autospec=True)
    def _test_push_web(self, scheme, length, request_mock=None):
        """
        Test pushing from a http/ftp url to the client, used
        by other test functions.

        Args:
            scheme: The scheme to be tested, either http[s] or ftp
            length: A boolean indicating wether the url should report
                    a content-length for checking.
        Returns:
            None

        Raises:
            AssertionError in case some validation failed
        """
        source_path = '/source/path'
        url = '{}://coolurl.cool{}'.format(scheme, source_path)
        target_path = '/target/path'

        read_data = [b'ab', b'cde', b'']

        source_fd = (request_mock.urlopen
                     .return_value.__enter__
                     .return_value)

        # urllib sets the content length in different places depending on the
        # scheme. If length is True, set the content-length to the full length
        # of read_data.
        if scheme == 'http' or scheme == 'https':
            if length:
                source_fd.length = (sum([len(data) for data in read_data]))
            else:
                source_fd.length = None
        else:
            assert scheme == 'ftp'
            if length:
                source_fd.info.return_value.get.return_value = (
                    sum([len(data) for data in read_data]))
            else:
                source_fd.info.return_value.get.return_value = None

        target_fd = self._mocked_sftp_write_fd

        source_fd.read.side_effect = read_data

        self._client.push_file(url, target_path)

        # Check urlopen was called with the url and the sftp
        # open function with the target path in write mode.
        request_mock.urlopen.assert_called_once_with(url)

        self._mocked_sftp_open.assert_called_once_with(
            target_path, 'wb')

        # Check that we wrote what we read.
        expected_read_calls = [mock.call(self._client.CHUNKSIZE)
                               for data in read_data]

        expected_write_calls = [mock.call(data)
                                for data in read_data[:-1]]

        self.assertEqual(source_fd.read
                         .call_args_list,
                         expected_read_calls)

        self.assertEqual(target_fd.write
                         .call_args_list,
                         expected_write_calls)

    def _test_transfer_ssh_ssh(self, method, source, target,
                               source_path, target_path):
        """
        Test pushing or pulling from/to self._client to/from
        another ssh host. Used by other test functions.

        For pushing the source should be a ssh url and the target
        a path (which refers to a path on self._client), for
        pulling the source should be a path and the target
        a ssh url.

        Args:
            method: The method object to be tested.
                    Either self._client.push_file or
                    self._client.pull_file.
            source: The ssh url for another host, when pushing,
                    or the path to a file on self._client when
                    pulling.
            target: The ssh url for another host, when pulling,
                    or the path to a file on self._client when
                    pushing.
            source_path: The file path on the source. Same as source
                         when pulling.
            target_path The file path on the target. Same as target
                        when pushing.
        Returns:
        Raises:
        """

        # The sftp open function mock will be the same for both ssh
        # hosts, since we use the same module for both.
        source_open = self._mocked_sftp_open
        target_open = source_open

        source_fd = self._mocked_sftp_read_fd
        target_fd = self._mocked_sftp_write_fd

        read_data = [b'ab', b'cde', b'']

        # Set the expected data to be read from the source.
        source_fd.read.side_effect = read_data

        # Write should return all bytes written.
        target_fd.write.side_effect = [len(data) for data in read_data[:-1]]

        method(source, target)

        # Check that we opened the source in read mode, and opened the target
        # in write mode. We use assertIn since the same mock is used for both
        # opens and we don't want to depend in which order the files
        # are opened.
        self.assertIn(mock.call(source_path, 'rb'),
                      source_open.call_args_list)

        self.assertIn(mock.call(target_path, 'wb'),
                      target_open.call_args_list)

        self.assertEqual(source_open.call_count, 2)

        # Check that we wrote what we read.
        expected_read_calls = [mock.call(self._client.CHUNKSIZE)
                               for data in read_data]

        expected_write_calls = [mock.call(data)
                                for data in read_data[:-1]]

        self.assertEqual(source_fd.read
                         .call_args_list,
                         expected_read_calls)

        self.assertEqual(target_fd.write
                         .call_args_list,
                         expected_write_calls)

    def test_change_file_perms_valid(self):
        """
        Test file permission change function for a valid permission
        bitfield.

        Args:
        Returns:
        Raises:
        """

        # should raise no exceptions for a valid permission field
        self._client.change_file_permissions('/fake/path', stat.S_IRUSR)

        self.assertEqual(self._client._sftp_conn.chmod.call_count,
                         1)

    def test_change_file_perms_invalid(self):
        """
        Test file permission change function for an invalid permission
        bitfield.

        Args:
        Returns:
        Raises:
        """

        with self.assertRaisesRegex(ValueError, 'Wrong permission format'):
            # 0o10000 goes beyond the 12 possible permission bits
            self._client.change_file_permissions('/fake/path', 0o10000)

        # chmod shouldn't have been called with the bad permission field
        self.assertEqual(self._client._sftp_conn.chmod.call_count,
                         0)

    def test_open_shell(self):
        """
        Test opening a shell with no problems.

        Args:
        Returns:
        Raises:
        """

        # Mock our shell class to simplify this test, since the shell
        # will try to run some initial commands.
        with mock.patch('tessia_baselib.common.ssh.client.SshShell',
                        autospec=True):

            shell = self._client.openShell(None, None)

            self.assertIsInstance(shell, shell_module.SshShell)

    def test_open_shell_bad_chroot_dir(self):
        """
        Test opening a shell with an inexistent chroot directory.

        Args:
        Returns:
        Raises:
        """

        self._client.path_exists = mock.MagicMock(return_value=False)

        with self.assertRaises(FileNotFoundError):
            self._client.openShell(chroot_dir='not-a-dir')

    def test_open_shell_bad_cmd(self):
        """
        Test opening a shell with an initial call to the shell binary
        that fails.

        Args:
        Returns:
        Raises:
        """

        # Recall that self._client._ssh_client is a mock.
        # Our client calls uses get_transport and then open_session
        # on the transport object to get a channel on which to call
        # exec_command. Here we make it so calling exec_command on
        # this returned channel will raise an exception.

        exception_text = 'test text for exception'

        (self._client._ssh_client
         .get_transport.return_value
         .open_session.return_value
         .exec_command.side_effect) = paramiko.SSHException(exception_text)

        with self.assertRaises(SshClientError) as assert_raises_context:
            self._client.openShell(None, None)

        self.assertIsInstance(assert_raises_context.exception.__cause__,
                              paramiko.SSHException)
        self.assertEqual(str(assert_raises_context.exception.__cause__),
                         exception_text)

    def test_open_shell_bad_path(self):
        """
        Test opening a shell with an inexistent shell binary.

        Args:
        Returns:
        Raises:
        """

        self._client.path_exists = mock.MagicMock(return_value=False)

        with self.assertRaises(FileNotFoundError):
            self._client.openShell(shell_path='not-a-dir')

    def test_open_shell_bad_session(self):
        """
        Test opening a shell and failing.

        Args:
        Returns:
        Raises:
        """

        exception_text = 'test text for exception'
        self._client._ssh_client.get_transport.side_effect = (
            paramiko.SSHException(exception_text))

        with self.assertRaises(IOError) as assert_raises_context:
            self._client.openShell(None, None)

        self.assertIsInstance(assert_raises_context.exception.__cause__,
                              paramiko.SSHException)
        self.assertEqual(str(assert_raises_context.exception.__cause__),
                         exception_text)

    def test_open_shell_good_chroot_dir(self):
        """
        Test opening a shell with a valid chroot directory.

        Args:
        Returns:
        Raises:
        """

        # Mock our sell class to simplify this test, since the shell
        # will try to run some initial commands.
        with mock.patch('tessia_baselib.common.ssh.client.SshShell',
                        autospec=True):

            self._client.path_exists = mock.MagicMock(return_value=True)

            chroot_dir = 'some_dir'
            self._client.openShell(chroot_dir=chroot_dir)

            exec_command_mock = (self._client._ssh_client
                                 .get_transport.return_value
                                 .open_session.return_value
                                 .exec_command)

            self.assertEqual(exec_command_mock.call_count, 1)

            # The first positional argument passed to exec_command
            # is the command.
            cmd = exec_command_mock.call_args[0][0]

            self.assertRegex(cmd, 'chroot {} .*'.format(chroot_dir))

    def test_open_shell_good_shell_path(self):
        """
        Test opening a shell with a valid shell binary.

        Args:
        Returns:
        Raises:
        """

        # Mock our sell class to simplify this test, since the shell
        # will try to run some initial commands.
        with mock.patch('tessia_baselib.common.ssh.client.SshShell',
                        autospec=True):

            self._client.path_exists = mock.MagicMock(return_value=True)

            self._client.openShell(shell_path='/bin/cool-shell')

    def test_path_exists_false(self):
        """
        Test a path check that returns that the path does not exist.

        Args:
        Returns:
        Raises:
        """

        # Force the open (file) call of sftp to raise a
        # FileNotFoundError exception.
        (self._client._ssh_client.open_sftp.
         return_value.file.side_effect) = FileNotFoundError('lolilol')

        self.assertFalse(self._client.path_exists('lol'))

    def test_path_exists_true(self):
        """
        Test a path check that returns that the path exists.

        Args:
        Returns:
        Raises:
        """

        # Path checks work by checking if an exception is
        # raised when the path doesn't exist. Since the library
        # is mocked this exception won't be raised and the path
        # will "exist".
        self.assertTrue(self._client.path_exists('lol'))

    def test_pull_file_bad_scheme(self):
        """
        Test pulling a file with an invalid scheme.

        Args:
        Returns:
        Raises:
        """
        url = 'http://cool_guy:cool_pw@cool_url.cool'
        with self.assertRaisesRegex(ValueError,
                                    'Invalid url scheme for pull operation'):
            self._client.pull_file('/some/path', url)

    @mock.patch('builtins.open', autospec=True)
    def test_pull_file_local(self, open_mock):
        """
        Test pulling a file from the ssh host to a local file.

        Args:
            open_mock: the patched builtin open function
        Returns:
        Raises:
        """

        source_path = '/source/file'
        target_path = '/target/file/;#?&@黃飛鴻'
        url = 'file://{}'.format(urllib.parse.quote(target_path))

        # Read from sftp.
        source_fd = self._mocked_sftp_read_fd

        # For writing to a local file, the file descriptor is expected
        # to be a BufferedWriter, otherwise an assertion in the tested class
        # fails.
        (open_mock.return_value
         .__enter__.return_value) = mock.MagicMock(spec_set=io.BufferedWriter)

        target_fd = open_mock.return_value.__enter__.return_value

        # Bytes that each call to read should return.
        read_data = [b'ab', b'cde', b'']

        source_fd.read.side_effect = read_data

        # Write should report all bytes written.
        target_fd.write.side_effect = [len(data) for data in read_data[:-1]]

        # The actual function we are testing.
        self._client.pull_file(source_path, url)

        # Since we are pulling, the sftp open function should have been
        # called in read mode, and the builtin open function in write
        # mode.
        self._mocked_sftp_open.assert_called_once_with(source_path, 'rb')

        open_mock.assert_called_once_with(target_path, 'wb')

        # Check that the function wrote to the target what it read
        # from the source.
        expected_read_calls = [mock.call(self._client.CHUNKSIZE)
                               for data in read_data]

        expected_write_calls = [mock.call(data)
                                for data in read_data[:-1]]

        self.assertEqual(source_fd.read.call_args_list,
                         expected_read_calls)

        self.assertEqual(target_fd.write.call_args_list,
                         expected_write_calls)

    def test_pull_file_ssh_default_port(self):
        """
        Test pulling a file from another ssh host without specifying a port.

        Args:
        Returns:
        Raises:
        """
        source_path = '/source/path'
        target_path_unquoted = '/target/file/;#?&@黃飛鴻'

        username_unquoted = 'c:o:o:l:g:u:y      ޏ₍ ὸ.ό₎ރ'
        password_unquoted = 'cool:p@ss///¯\\_(ツ)_/¯'
        hostname_unquoted = 'verystupid#@?hostname:!;_-==.whatisthisツdomain'
        url = 'ssh://{}:{}@{}{}'.format(
            urllib.parse.quote(username_unquoted, errors='strict', safe=''),
            urllib.parse.quote(password_unquoted, errors='strict', safe=''),
            urllib.parse.quote(hostname_unquoted, errors='strict', safe=''),
            urllib.parse.quote(target_path_unquoted, errors='strict'))

        # Reset the connect mock, since it was already used once to
        # log in self._client and we want to check how it is called
        # to log in the second ssh client in the ssh url.
        self._mocked_paramiko_client.return_value.connect.reset_mock()

        # Pass the unquoted target_path, so that _test_transfer_ssh_ssh
        # checks if 'open_file' is called on the unquoted path as it should.
        # This tests if pull_file unquoted the path before calling 'open_file'.
        self._test_transfer_ssh_ssh(self._client.pull_file, source_path, url,
                                    source_path, target_path_unquoted)

        expected_kwargs = {'hostname': hostname_unquoted,
                           'username': username_unquoted,
                           'password': password_unquoted,
                           'port': 22}

        connect_kwargs = (self._mocked_paramiko_client
                          .return_value.connect.call_args[1])

        # Check if the unquoted username, password, hostname
        # and the default port 22 were used to connect to the ssh host.
        # This checks if the module unquoted these components of the
        # url before connecting.
        for expected_kwarg_key in iter(expected_kwargs):
            self.assertEqual(expected_kwargs[expected_kwarg_key],
                             connect_kwargs[expected_kwarg_key])

    def test_pull_file_ssh_no_path(self):
        """
        Test that pulling a file to a ssh url with no path
        fails.

        Args:
        Returns:
        Raises:
        """
        url = 'ssh://cool_guy:cool_pw@cool_url.cool'

        with self.assertRaisesRegex(ValueError, 'Empty file path in url'):
            self._client.pull_file('/source/file', url)

    def test_pull_file_ssh_no_hostname(self):
        """
        Test that pulling a file to a ssh url with no host
        fails.

        Args:
        Returns:
        Raises:
        """
        url = 'ssh:///some/path'

        with self.assertRaisesRegex(ValueError, 'Hostname is empty'):
            self._client.pull_file('/source/file', url)

    def test_pull_file_ssh_no_userpass(self):
        """
        Test pulling a file to another ssh host without a username
        and password.

        Args:
        Returns:
        Raises:
        """
        url = 'ssh://[fe80::661c:67ff:fe7a:3fd4]/some/path'

        self._client.pull_file('/source/file', url)

    def test_pull_file_ssh_other_port(self):
        """
        Test pulling a file to another ssh host with a non-default port.

        Args:
        Returns:
        Raises:
        """
        port = 451
        source_path = '/source/path'
        target_path = '/target/file/;#?&@黃飛鴻'
        url = 'ssh://cool_guy:cool_pw@cool_url.cool:{}{}'.format(
            port, urllib.parse.quote(target_path))

        # Reset the connect mock, since it was already used once to
        # log in self._client and we want to check how it is called
        # to log in the second ssh client in the ssh url.
        self._mocked_paramiko_client.return_value.connect.reset_mock()

        self._test_transfer_ssh_ssh(self._client.pull_file, source_path,
                                    url, source_path, target_path)

        # Test that the port we passed in the url was used to open
        used_port = (self._mocked_paramiko_client
                     .return_value.connect.call_args[1]['port'])

        self.assertEqual(used_port, port)

    def test_push_file_bad_url(self):
        """
        Test pushing a file with an invalid scheme.

        Args:
        Returns:
        Raises:
        """
        url = 'ttt://cool_guy:cool_pw@cool_url.cool/source/path'
        with self.assertRaisesRegex(ValueError,
                                    'Invalid url scheme for push operation'):
            self._client.push_file(url, '/target/path/')

    @mock.patch('builtins.open', autospec=True)
    def test_push_file_local(self, open_mock):
        """
        Test pushing a local file to the ssh host.

        Args:
            open_mock: the patched builtin open function
        Returns:
        Raises:
        """

        source_path = '/source/file;#?&@黃飛鴻'
        url = 'file://{}'.format(urllib.parse.quote(source_path))
        target_path = '/target/file'

        # Bytes that each call to read should return.
        read_data = [b'ab', b'cde', b'']

        source_fd = open_mock.return_value.__enter__.return_value

        target_fd = self._mocked_sftp_write_fd

        source_fd.read.side_effect = read_data

        # Write should return all bytes written.
        target_fd.write.side_effect = [len(data) for data in read_data[:-1]]

        self._client.push_file(url, target_path)

        # Since we are pushing, the builtin read function should have
        # been called in read mode, and the sftp open function in
        # write mode.
        open_mock.assert_called_once_with(source_path, 'rb')

        self._mocked_sftp_open.assert_called_once_with(target_path, 'wb')

        # Check that we write to target what we read from source.
        expected_read_calls = [mock.call(self._client.CHUNKSIZE)
                               for data in read_data]

        expected_write_calls = [mock.call(data)
                                for data in read_data[:-1]]

        self.assertEqual(source_fd.read.call_args_list,
                         expected_read_calls)

        self.assertEqual(target_fd.write.call_args_list,
                         expected_write_calls)

    def test_push_file_ssh(self):
        """
        Test pushing a file from another ssh host to self._client.

        Args:
        Returns:
        Raises:
        """
        source_path = '/source/file;#?&@黃飛鴻'
        url = 'ssh://cool_guy:cool_pw@cool_url.cool{}'.format(
            urllib.parse.quote(source_path))

        target_path = '/target/file'

        self._test_transfer_ssh_ssh(self._client.push_file,
                                    url, target_path,
                                    source_path, target_path)

    @mock.patch('urllib.request', autospec=True)
    def test_push_ftp_bad_length(self, request_mock):
        """
        Test pushing a a file from an ftp url that reports an incorrect
        content length.

        Args:
        Returns:
        Raises:
        """
        url = 'ftp://coolurl.cool/source/path'

        (request_mock.urlopen.return_value
         .__enter__.return_value
         .info.return_value
         .get.return_value) = 1

        (request_mock.urlopen
         .return_value.__enter__
         .return_value.read.side_effect) = [b'abcd', b'']

        # 1 is smaller than the length of the data below.
        with self.assertRaisesRegex(IOError, 'Read incomplete file.*'):
            self._client.push_file(url, '/target/path')

    def test_push_ftp_with_length(self):
        """
        Test pushing a a file from an ftp url that
        reports the correct content length.

        Args:
        Returns:
        Raises:
        """
        self._test_push_web('ftp', True)

    def test_push_ftp_without_length(self):
        """
        Test pushing a a file from an ftp url that
        does not report the content length.

        Args:
        Returns:
        Raises:
        """
        self._test_push_web('ftp', False)

    @mock.patch('urllib.request', autospec=True)
    def test_push_http_bad_length(self, request_mock):
        """
        Test pushing a a file from an http url that reports an incorrect
        content length.

        Args:
        Returns:
        Raises:
        """
        url = 'http://coolurl.cool/source/path'

        # 1 is smaller than the length of the data below.
        request_mock.urlopen.return_value.__enter__.return_value.length = 1

        (request_mock.urlopen
         .return_value.__enter__
         .return_value.read.side_effect) = [b'abcd', b'']

        with self.assertRaisesRegex(IOError, 'Read incomplete file.*'):
            self._client.push_file(url, '/target/path')

    def test_push_http_with_length(self):
        """
        Test pushing a a file from an http url that
        reports a correct content length.

        Args:
        Returns:
        Raises:
        """
        self._test_push_web('http', True)

    def test_push_http_without_length(self):
        """
        Test pushing a a file from an http url that
        does not report the content length.

        Args:
        Returns:
        Raises:
        """
        self._test_push_web('http', False)


class TestSshClientNotConnected(unittest.TestCase):
    """
    Test class for the SshClient class.

    This class only tests logging in/logging off methods
    and methods that do not require the client to be logged in.
    """
    def setUp(self):
        """
        Setup function called before every test_* function.

        Patch the paramiko SSHClient with a mock.

        Args:
        Returns:
        Raises:
        """
        # Create a patcher to replace the paramiko SSHClient
        # class with a mock, this way no actual connection to
        # a real ssh server is needed.
        patcher = mock.patch(
            target='tessia_baselib.common.ssh.client.paramiko.SSHClient',
            autospec=True)

        # Activate the patch. The attribute will hold the mocked class.
        # The 'return_value' attribute of the mocked class is the same value
        # produced when the class is instantiated in the tested code.
        self._paramiko_client_class_mock = patcher.start()
        self.addCleanup(patcher.stop)

        # patch the function that gets a logger so that the test does not try
        # to create real log file on the filesystem
        log_patcher = mock.patch(
            'tessia_baselib.common.ssh.client.getLogger', autospec=True)
        self._mock_getlogger = log_patcher.start()
        self.addCleanup(log_patcher.stop)

        self._mock_logger = mock.MagicMock(spec_set=logging.Logger)
        self._mock_getlogger.return_value = self._mock_logger

        self._client = client.SshClient()

    def test_assert_connected(self):
        """
        Test logged in assertion.

        Args:
        Returns:
        Raises:
        """
        with self.assertRaisesRegex(IOError, 'Not connected'):
            self._client._assert_connected()

        self._client.login(host_name=HOST_NAME, port=PORT,
                           user=USERNAME, passwd=PASSWORD)

        # should no longer raise an exception
        self._client._assert_connected()

    def test_login(self):
        """
        Test a regular login.

        Args:
        Returns:
        Raises:
        """
        self._client.login(host_name=HOST_NAME, port=PORT,
                           user=USERNAME, passwd=PASSWORD)

        self.assertEqual(self._client._ssh_client.connect.call_count, 1)
        self.assertEqual(self._client._ssh_client.open_sftp.call_count, 1)

        # Make sure the connection objects were created.
        self.assertIsNot(self._client._ssh_client, None)
        self.assertIsNot(self._client._sftp_conn, None)

    def test_login_auth_exception(self):
        """
        Test a failed login that raises PermissionError.

        Args:
        Returns:
        Raises:
        """
        exception_text = 'test text for exception'

        (self._paramiko_client_class_mock
         .return_value
         .connect
         .side_effect) = paramiko.AuthenticationException(exception_text)

        with self.assertRaises(PermissionError) as assert_raises_context:
            self._client.login(host_name=HOST_NAME, port=PORT,
                               user=USERNAME, passwd=PASSWORD)

        self.assertIsInstance(assert_raises_context.exception.__cause__,
                              paramiko.AuthenticationException)
        self.assertEqual(str(assert_raises_context.exception.__cause__),
                         exception_text)

    def test_login_exception(self):
        """
        Test a failed login that raises ConnectionError.

        Args:
        Returns:
        Raises:
        """
        exception_text = 'test text for exception'

        (self._paramiko_client_class_mock
         .return_value
         .connect
         .side_effect) = Exception(exception_text)

        with self.assertRaises(ConnectionError) as assert_raises_contex:
            self._client.login(host_name=HOST_NAME, port=PORT,
                               user=USERNAME, passwd=PASSWORD)

        self.assertEqual(str(assert_raises_contex.exception.__cause__),
                         exception_text)

    def test_login_open_sftp_exception(self):
        """
        Test a login that fails when opening the sftp
        channel fails.

        Args:
        Returns:
        Raises:
        """
        exception_text = 'test text for exception'

        # Force open_sftp to raise an exception
        (self._paramiko_client_class_mock
         .return_value
         .open_sftp
         .side_effect) = Exception(exception_text)

        with self.assertRaises(ConnectionError) as assert_raises_contex:
            self._client.login(host_name=HOST_NAME, port=PORT,
                               user=USERNAME, passwd=PASSWORD)

        self.assertEqual(str(assert_raises_contex.exception.__cause__),
                         exception_text)

        self.assertIs(self._client._ssh_client, None)
        self.assertIs(self._client._sftp_conn, None)

    def test_login_active_connection(self):
        """
        Test a login with a class that has already logged in.

        Args:
        Returns:
        Raises:
        """
        self._client.login(host_name=HOST_NAME, port=PORT,
                           user=USERNAME, passwd=PASSWORD)

        # The first login should issue no warnings.
        self.assertFalse(self._client._logger_obj.warning.called)

        self._client.login(host_name=HOST_NAME, port=PORT,
                           user=USERNAME, passwd=PASSWORD)

        # Double logging-in will cause a warning to be issued.
        self.assertTrue(self._client._logger_obj.warning.called)

    def test_logoff(self):
        """
        Test a logoff after a login.

        Args:
        Returns:
        Raises:
        """
        self._client.login(host_name=HOST_NAME, port=PORT,
                           user=USERNAME, passwd=PASSWORD)

        self.assertIsNot(self._client._ssh_client, None)
        self.assertIsNot(self._client._sftp_conn, None)

        self._client.logoff()

        # Make sure the connection objects were cleared.
        self.assertIs(self._client._ssh_client, None)
        self.assertIs(self._client._sftp_conn, None)

        # Test logging of when sftp connection was not crated
        # (this happ
        self._client.login(host_name=HOST_NAME, port=PORT,
                           user=USERNAME, passwd=PASSWORD)

    def test_logoff_no_login(self):
        """
        Test a logoff without first having logged in.

        Args:
        Returns:
        Raises:
        """
        self._client.logoff()

        # Check if the logger issued a warning.
        self.assertTrue(self._client._logger_obj.warning.called)


if __name__ == '__main__':
    unittest.main()
