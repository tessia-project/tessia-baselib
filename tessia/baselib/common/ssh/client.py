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
Module for a ssh client class.
"""

#
# IMPORTS
#
from tessia.baselib.common.logger import get_logger
from tessia.baselib.common.ssh.exceptions import SshClientError
from tessia.baselib.common.ssh.shell import SshShell

import io
import logging
import paramiko
import stat
import urllib.parse
import urllib.request


#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
class SshClient:
    """
    This class provides a client for SSH communication and encapsulates the
    implementation details of the underlying library used.
    Implementation detail: we might want to use different underlying library in
    the future (instead of paramiko) so we catch, log and rethrow the
    exceptions raised by the library in order to have a stable interface
    with the upper layers.
    """

    CHUNKSIZE = io.DEFAULT_BUFFER_SIZE
    URL_UNQUOTE_ERRORS = 'strict'

    def __init__(self):
        """
        Constructor. Initializes object variables and logging

        Args:
            None

        Raises:
            None
        """
        # intialize logger object
        self._logger = get_logger(__name__)

        self._private_key_path = None
        self._timeout = None

        # connection object
        self._ssh_client = None
        # sftp stream object
        self._sftp_conn = None
    # __init__()

    def _assert_connected(self):
        """
        Ensure that login has been successfully called on this object.

        Args:
            None

        Raises:
            OSError: see IOError
            IOError: if login has not been successfully called on this object
        """
        # connection not active: fail operation
        if self._ssh_client is None:
            raise IOError('Not connected')
    # _assert_connected()

    def _check_and_unquote_path(self, quoted_path):
        """
        Take a string representing a path from a url, check if it is
        empty, and if not return it with unquoted %xx escapes.

        Args:
            quoted_path (str): a url-quoted path

        Returns:
            str: The unquoted path, if the path is not empty

        Raises:
            ValueError: if the path is empty
        """
        if not quoted_path:
            raise ValueError('Empty file path in url')

        return urllib.parse.unquote(quoted_path,
                                    errors=self.URL_UNQUOTE_ERRORS)
    # _check_and_unquote_path()

    @staticmethod
    def _chunked_copy(source_fd, target_fd, chunk_size=CHUNKSIZE):
        """
        Copy bytes from one file descriptor to another in fixed-size chunks.

        Args:
            source_fd (stream): open file descriptor to read from, must be a
                                byte stream
            target_fd (stream): open file descriptor to write to, either a
                                BufferedWriter or paramiko.sftp_file, must be
                                a byte stream in blocking mode
            chunk_size (int): maximum number of bytes to read from source_fd
                              before copying them to target_fd

        Returns:
            int: number of bytes copied from the source to the target

        Raises:
            AssertionError on unexpected conditions
        """
        # Only accept these types of target file descriptors,
        # so that we can assume each call to write will consume
        # all the bytes we give to it. If this changes
        # it might be necessary to loop around multiple write
        # calls to ensure all bytes are consumed by the write call
        # (e.g. with raw io).
        is_sftp = isinstance(target_fd, paramiko.SFTPFile)
        is_buffered_writer = isinstance(target_fd, io.BufferedWriter)
        assert is_buffered_writer or is_sftp

        if is_sftp:
            # Set pipelined to true so that sftp writes don't wait
            # for a response every time. If something goes wrong
            # an exception will be thrown when the file is closed.
            target_fd.set_pipelined(True)

        n_bytes_copied = 0

        while True:
            bytes_read = source_fd.read(chunk_size)

            n_bytes_read = len(bytes_read)

            # EOF found: stop copying
            if n_bytes_read == 0:
                break

            # read return bytes: write tem to target_fd
            n_bytes_written = target_fd.write(bytes_read)

            # target_fd is a BufferedWriter: return value of it is a number
            # and we can check it
            if is_buffered_writer:
                # Make sure BufferedWriter really wrote
                # or buffered all the bytes we gave it.
                # This should be the case but the python
                # documentation is ambiguous.
                # The paramiko file descriptor always
                # returns None, so we don't check it.
                assert n_bytes_written == n_bytes_read

            n_bytes_copied += n_bytes_read

        return n_bytes_copied
    # _chunked_copy()

    def _make_ssh_client(self, parsed_url):
        """
        Create a new ssh client object and log it into the
        ssh host passed as a parameter.

        The private key path and connection timeout values
        used are the same as the ones set for the 'self' object.

        Args:
            parsed_url (tuple): returned by urllib.parse.urlsplit parsed from
                                an ssh url. The hostname must be non-empty.

        Returns:
            SshClient: Instance connected to the host defined in
                       the url parameter

        Raises:
            ValueError: if there is no hostname in the url
        """
        # no host name: fail operation
        if parsed_url.hostname is None:
            raise ValueError('Hostname is empty')
        host_name = urllib.parse.unquote(
            parsed_url.hostname,
            errors=self.URL_UNQUOTE_ERRORS)

        username = parsed_url.username
        if username is not None:
            username = urllib.parse.unquote(
                username,
                errors=self.URL_UNQUOTE_ERRORS)

        password = parsed_url.password
        if password is not None:
            password = urllib.parse.unquote(
                password,
                errors=self.URL_UNQUOTE_ERRORS)

        kwargs = {
            'user': username,
            'passwd': password,
            'timeout': self._timeout,
        }

        # Don't pass None as a port to login, use
        # the default port by not setting it in kwargs.
        if parsed_url.port is not None:
            # No need to unquote the port since it should just be a
            # number.
            kwargs['port'] = parsed_url.port

        # login to target system
        other_ssh_client = SshClient()
        other_ssh_client.login(host_name, **kwargs)

        return other_ssh_client
    # _make_ssh_client()

    def _open_sftp_session(self):
        """
        Open a sftp session if it is not open yet.

        Args:
            None

        Raises:
            ConnectionError: If there is an error while creating the session.
        """
        # Verify if there is an open sftp session.
        if self._sftp_conn is not None:
            return

        # It is not obligatory to close the ssh connection if the sftp session
        # fails to open.
        try:
            sftp_conn = self._ssh_client.open_sftp()
        except Exception as exc:
            raise ConnectionError(str(exc)) from exc

        self._sftp_conn = sftp_conn
    # _open_sftp_session()

    def _pull_to_file(self, source_file_path, target_file_path,
                      write_mode):
        """
        Copy a file from this ssh host to the local filesystem (where this
        module runs).

        Args:
            source_file_path (str): A file path on the ssh host.
            target_file_path (str): A file on this local host.
            write_mode (str): 'wb' or 'ab' for truncating or appending.

        Raises:
            None
        """
        with self.open_file(source_file_path, 'rb') as source_fd,\
             open(target_file_path, write_mode) as target_fd:
            self._chunked_copy(source_fd, target_fd)
    # _pull_to_file()

    def _pull_to_ssh(self, source_file_path, parsed_target_url,
                     write_mode):
        """
        Copy a file from this ssh host to another ssh host.

        A new client to another ssh host is created, the file is copied between
        this host and the other one, and then the other one is closed.

        Args:
            source_file_path (str): A path to the file on this ssh host.
            parsed_target_url (tuple): returned by urllib.parse.urlsplit
                                       parsed from an ssh url, indicating the
                                       target file.
            write_mode (str): Either 'wb' or 'ab' for truncating or appending.

        Raises:
            None
        """
        other_ssh_client = self._make_ssh_client(parsed_target_url)

        path = self._check_and_unquote_path(parsed_target_url.path)

        try:
            with self.open_file(source_file_path, 'rb')\
                 as source_fd,\
            other_ssh_client.open_file(path, write_mode)\
                 as target_fd:
                self._chunked_copy(source_fd, target_fd)
        finally:
            other_ssh_client.logoff()
    # _pull_to_ssh()

    def _push_from_ssh(self, parsed_source_url, target_file_path,
                       write_mode):
        """
        Copy a file from another ssh host to this ssh host.

        A new client to another ssh host is created, the file is copied between
        this host and the other one, and then the other one is closed.

        Args:
            parsed_source_url (tuple): tuple returned by urllib.parse.urlsplit
                                       parsed from an ssh url, indicating the
                                       source file.
            target_file_path (str): A path to the file on this ssh host.
            write_mode (str): Either 'wb' or 'ab' for truncating or appending.

        Raises:
            None
        """

        other_ssh_client = self._make_ssh_client(parsed_source_url)

        path = self._check_and_unquote_path(parsed_source_url.path)

        try:
            with other_ssh_client.open_file(path, 'rb') as source_fd, \
                 self.open_file(target_file_path, write_mode) as target_fd:
                self._chunked_copy(source_fd, target_fd)
        finally:
            other_ssh_client.logoff()
    # _push_from_ssh()

    def _push_from_web(self, parsed_source_url, source_url,
                       target_file_path, write_mode):
        """
        Copy a file from a http, https or fpt url to a file on this
        ssh host.

        Args:
            parsed_source_url (tuple): returned by urllib.parse.urlsplit
                                       from parsing the source url
            source_url (str): The unparsed full source url.
            target_file_path (str): A path to the file on this ssh host.
            write_mode (str): Either 'wb' or 'ab' for truncating or appending.

        Raises:
            OSError: see IOError
            IOError: If the source url reports a content-length and this
                     length does not match the copied length.
        """

        scheme = parsed_source_url.scheme

        with urllib.request.urlopen(source_url) as source_fd, \
             self.open_file(target_file_path, write_mode) as target_fd:

            length = None

            # url is http[s]: get content-length from length attribute
            if scheme in ['http', 'https']:
                if source_fd.length is not None:
                    length = source_fd.length
            # url is ftp: get content-length from info object
            else:
                # See urlib.request/urlib.response to see
                # how this length is set for a ftp response.
                length = source_fd.info().get('Content-Length')

                if length is not None:
                    length = int(length)

            read_bytes = self._chunked_copy(source_fd, target_fd)

            # Content length was reported and it does not match the amount of
            # bytes we read: raise exception.
            if length is not None and read_bytes != length:
                raise IOError('Read incomplete file: expected {} bytes, got {}'
                              .format(length, read_bytes))
    # _push_from_web()

    def _push_local_file(self, source_file_path, target_file_path, write_mode):
        """
        Copy a file from the local host to this ssh host.

        Args:
            source_file_path (str): A file on this local host.
            target_file_path (str): A file on this ssh host.
            write_mode (str): 'wb' or 'ab' for truncating or appending.

        Raises:
            None
        """
        with open(source_file_path, 'rb') as source_fd, \
             self.open_file(target_file_path, write_mode) as target_fd:
            self._chunked_copy(source_fd, target_fd)
    # _push_local_file()

    def change_file_permissions(self, file_path, file_perms):
        """
        Change permissions of a file in the target system.

        Args:
            file_path (str): file path on target system
            file_perms (int): integer containing the permission bits
                              (as defined by os.chmod)
        Raises:
            ValueError: if permission is in a wrong format

        """
        self._assert_connected()
        self._open_sftp_session()

        # perform sanity check
        try:
            # make sure it's an integer
            file_perms = int(file_perms)
            # exception is raised in case number is out of range
            check_perms = stat.S_IMODE(file_perms)
            # number might be within range but stat had to convert, so
            # in order to avoid inconsistency we also fail in that case
            assert check_perms == file_perms
        except Exception as exc:
            raise ValueError('Wrong permission format') from exc

        self._sftp_conn.chmod(file_path, file_perms)
    # change_file_permissions()

    def login(self, host_name, port=22, user=None, passwd=None,
              private_key_str=None, timeout=60):
        """
        Establishes a connection to the target system

        Args:
            host_name (str): target hostname
            port (int): optional ssh port to use
            user (str): username for connection, disregarded if
                        private_key_path is specified
            passwd (str): password for connection, disregarded if
                          private_key_path is specified
            private_key_str (str): a RSA private key to use for authentication
            timeout (int): how many seconds to wait for connection to complete

        Raises:
            ConnectionError: if protocol or network error occurred
            PermissionError: if login failed because credentials are invalid
            ValueError: in case an invalid private key (i.e. not RSA) is
                        provided
        """
        # existing connection: warn in log
        if self._ssh_client is not None:
            self._logger.warning('login called with connection active: '
                                 'dropping previous connection object')

        # debugging information on connection
        if private_key_str:
            try:
                key_obj = paramiko.RSAKey.from_private_key(
                    file_obj=io.StringIO(private_key_str))
            except paramiko.ssh_exception.SSHException as exc:
                raise ValueError(
                    'Invalid private key provided: {}'.format(str(exc)))
            key_str = key_obj.get_base64()
        else:
            key_obj = None
            key_str = 'None'
        self._logger.debug(
            "login: hostname='%s' port='%s' user='%s' priv_key='%s' "
            "timeout='%s'", host_name, port, user, key_str, timeout
        )

        # create underlying library object
        ssh_client = paramiko.SSHClient()
        ssh_client.set_log_channel('paramiko')
        paramiko_logger = logging.getLogger('paramiko')
        # logger not configured: make it silent
        if not paramiko_logger.hasHandlers():
            paramiko_logger.addHandler(logging.NullHandler())
        # set policy to add unknown host keys
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # try to connect and catch possible problems
        try:
            ssh_client.connect(
                hostname=host_name,
                port=port,
                username=user,
                password=passwd,
                pkey=key_obj,
                timeout=timeout,
                # disable usage of SSH agent
                allow_agent=False,
                # disable looking for keys in ~/.ssh
                look_for_keys=False
            )
        # credentials invalid
        except paramiko.AuthenticationException as exc:
            # log the traceback for possible debugging
            self._logger.debug('login exception:', exc_info=True)

            # report our custom exception so that upper layers do not tie to
            # the underlying implementation
            raise PermissionError('Invalid credentials') from exc

        # other errors (i.e. protocol or connection errors)
        except Exception as exc:
            # log the traceback for possible debugging
            self._logger.debug('login exception:', exc_info=True)

            # report our custom exception so that upper layers do not tie to
            # the underlying implementation
            raise ConnectionError(str(exc)) from exc

        # store instance values
        self._ssh_client = ssh_client
        self._timeout = timeout
    # login()

    def logoff(self):
        """
        Close connection to target system. This function is not expected to
        raise any exception by the library.

        Args:
            None

        Raises:
            None
        """
        # no connection active: nothing to do
        if self._ssh_client is None:
            self._logger.warning('logoff called but no connection active: '
                                 'ignoring')
            return

        # according to paramiko no exception can be raised while closing a
        # connection
        self._logger.debug('closing connection')

        # a sftp session exists: close it
        if self._sftp_conn is not None:
            self._sftp_conn.close()
            self._sftp_conn = None

        self._ssh_client.close()
        self._ssh_client = None
    # logoff()

    def open_file(self, file_path, mode):
        """
        Open a file on the target system.

        Args:
            file_path (str): path of the file on the target system
            mode (str): open mode

        Returns:
            object: A file-like object handle

        Raises:
            None
        """

        self._assert_connected()
        self._open_sftp_session()

        return self._sftp_conn.open(file_path, mode)
    # open_file()

    def open_shell(self, chroot_dir=None, shell_path=None):
        """
        Open an interactive shell and return an expect-like object. Optionally
        accepts a directory to perform chroot.

        Args:
            chroot_dir (str): directory to perform chroot
            shell_path (str): path where shell is located (defaults to /bin/sh)

        Returns:
            SshShell: object

        Raises:
            OSError: see IOError
            IOError: if session cannot be opened
            FileNotFoundError: if chroot dir does not exist
            SshClientError: if shell cannot be started
        """
        self._logger.debug(
            "open_shell: chroot_dir='%s' shell_path='%s'",
            chroot_dir, shell_path)

        self._assert_connected()

        # chroot directory does not exist: abort
        if chroot_dir and not self.path_exists(chroot_dir):
            raise FileNotFoundError(
                'Chroot dir {} does not exist'.format(chroot_dir)
            )

        # shell not specified: use default
        if shell_path is None:
            shell_path = '/bin/sh'
        # shell specified does not exist: cannot continue
        elif not self.path_exists(shell_path):
            raise FileNotFoundError(
                'Shell {} does not exist'.format(shell_path)
            )

        # open a new session to be used to run the shell process
        self._logger.debug('calling get_transport.open_session()')
        try:
            channel = self._ssh_client.get_transport().open_session(timeout=15)
        except paramiko.SSHException as exc:
            self._logger.debug(
                'open_shell open_session exception:', exc_info=True)
            raise IOError(
                'Failed to open shell: {}'.format(str(exc))) from exc

        # term dumb is important to avoid escape sequences
        # width is important to not truncate long command lines
        self._logger.debug('calling channel.get_pty()')
        channel.get_pty(term='dumb', width=10000)
        # put stdout and stderr in same stream
        channel.set_combine_stderr(True)

        # use -s to make the shell read from stdin and -l to make it a login
        # shell so that .profile is loaded
        shell_cmd = '{} -s -l'.format(shell_path)
        # directory specified: chroot to it
        if chroot_dir:
            shell_cmd = 'chroot %s %s' % (chroot_dir, shell_cmd)
        # start the shell command
        self._logger.debug('calling channel.exec_command()')
        try:
            channel.exec_command(shell_cmd)
        except paramiko.SSHException as exc:
            # log the exception for debugging and raise our own to decouple
            # user from implementation detail
            self._logger.debug(
                'open_shell exec_command exception:', exc_info=True)
            raise SshClientError(
                'Failed to start shell: {}'.format(str(exc))) from exc

        return SshShell(channel)
    # open_shell()

    def path_exists(self, check_path):
        """
        Verifies if a given path exists on system

        Args:
            check_path (str): filesystem path

        Returns:
            bool: True if path exists, False otherwise

        Raises:
            None
        """
        self._assert_connected()
        self._open_sftp_session()

        # try to open a file descriptor to file
        try:
            file_fd = self._sftp_conn.file(check_path, 'r')
        # not found exception raised: path does not exist
        except FileNotFoundError:
            return False

        # close filehandle
        file_fd.close()

        return True
    # path_exists()

    def pull_file(self, source_file_path, target_url, write_mode='wb'):
        """
        Retrieve a file from this ssh host through sftp and copy it to the
        target url.

        Args:
            source_file_path (str): Path of the file in this ssh host
            target_url (str): Url to which the source file should be copied.
                              The following schemes are accepted:
                              ssh://[user[:pass]]@ssh_host[:port]/target/path
                              file:///target/path
                              A ssh url refers to a file on another ssh host.
                              A file url refers to a file on the local host,
                              and any host portion of the url is ignored.
                              The url has to be properly quoted.
                              See urllib.parse.quote. Don't forget to call it
                              with safe='/' when quoting paths and safe='' when
                              quoting other components (e.g. the password,
                              which could contain a '/' and must be quoted).
            write_mode (str): Either 'wb' or 'ab', for truncating and appending
                              to the target file, respectively.
        Raises:
            AssertionError: if write_mode is invalid
            ValueError: if the url contains an unsupported scheme.
        """

        self._assert_connected()

        assert write_mode in ['wb', 'ab']

        parsed_url = urllib.parse.urlsplit(target_url)

        # target is another ssh host: pull source to it
        if parsed_url.scheme == 'ssh':
            self._pull_to_ssh(source_file_path, parsed_url,
                              write_mode)
        # target is a local file: write source to it
        elif parsed_url.scheme == 'file':
            self._pull_to_file(
                source_file_path,
                self._check_and_unquote_path(parsed_url.path), write_mode)

        # any other scheme: not supported, fail operation
        else:
            raise ValueError('Invalid url scheme for pull operation')
    # pull_file()

    def push_file(self, source_url, target_file_path, write_mode='wb'):
        """
        Retrieve a file from source_url and copy it to a file on this
        ssh host.

        Args:
            source_url (str): Url to which the source file should be copied.
                              The following schemes are accepted:
                              ssh://[user[:pass]]@ssh_host[:port]/target/path
                              file:///target/path
                              http, https or ftp urls

                              A ssh url refers to a file on another ssh host.
                              A file url refers to a file on the local host,
                              and any host portion of the url is ignored.

                              The url has to be properly quoted.
                              See urllib.parse.quote. Don't forget to call it
                              with safe='/' when quoting paths and safe=''
                              when quoting other components (e.g. the password,
                              which could contain a '/' which must be quoted).

            target_file_path (str): Path of the file in this ssh host to which
                                    the source will be copied.
            write_mode (str): Either 'wb' or 'ab', for truncating and appending
                              to the target file, respectively.

        Raises:
            ValueError: if the url contains an unsupported scheme.
        """
        self._assert_connected()

        assert write_mode in ['wb', 'ab']

        parsed_url = urllib.parse.urlsplit(source_url)

        scheme = parsed_url.scheme

        # source is a file on another ssh host: read file from it and push it
        if scheme == 'ssh':
            self._push_from_ssh(parsed_url, target_file_path,
                                write_mode)
        # source is a local file: read it and push it
        elif scheme == 'file':
            self._push_local_file(
                self._check_and_unquote_path(parsed_url.path),
                target_file_path, write_mode)

        # source is a http[s] or ftp rul: request it and push the file
        elif scheme in ['http', 'https', 'ftp']:
            self._push_from_web(parsed_url, source_url,
                                target_file_path, write_mode)
        # any other scheme: no supported, fail operation
        else:
            raise ValueError('Invalid url scheme for push operation')
    # push_file()

# SshClient
