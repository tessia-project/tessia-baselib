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

#
# IMPORTS
#
from tessia_baselib.common.logger import getLogger
from tessia_baselib.common.ssh.exceptions import SshClientError
from tessia_baselib.common.ssh.shell import SshShell

import paramiko
import stat

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
class SshClient(object):
    """
    This class provides a client for SSH communication and encapsulates the
    implementation details of the underlying library used.
    Implementation detail: we might want to use different underlying library in
    the future (instead of paramiko) so we catch, log and rethrow the exceptions
    raised by the library in order to have a stable interface with the upper layers.
    """

    def __init__(self):
        """
        Constructor. Initializes object variables and logging

        Args:
            None

        Returns:
            None

        Raises:
            None
        """
        # intialize logger object
        self._loggerObj = getLogger(__name__)

        # connection parameters
        self.host_name = None
        self.user = None
        self.passwd = None
        self.port = None
        self.private_key_path = None

        # connection object
        self._sshClient = None
        # sftp stream object
        self._sftpConn = None
    # __init__()

    def login(self, host_name, port=22, user=None, passwd=None,
              private_key_path=None, timeout=60):
        """
        Stablishes a connection to the target system

        Args:
            host_name: target hostname
            port: optional ssh port to use
            user: username for connection, disregarded if private_key_path is
                  specified
            passwd: password for connection, disregarded if private_key_path is
                    specified
            private_key_path: directory path containing private keys to use
            timeout: how many seconds to wait for connection to complete

        Returns:
            None

        Raises:
            ConnectionError: if protocol or network error occurred
            PermissionError: if login failed because credentials are invalid
        """
        # store instance values
        self.host_name = host_name
        self.port = port
        self.user = user
        self.passwd = passwd
        self.private_key_path = private_key_path

        # existing connection: warn in log
        if self._sshClient is not None:
            self._loggerObj.warn('login called with connection active: '
                                'dropping previous connection object')

        # debugging information on connection
        self._loggerObj.debug(
            "login: hostname='%s' port='%s' user='%s' priv_key='%s' "
            "timeout='%s'", self.host_name, self.port, self.user,
            self.private_key_path, timeout
        )

        # create library object with policy to add unknown host keys
        sshClient = paramiko.SSHClient()
        sshClient.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # change default's paramiko channel name to our module structure, it
        # is easier for logging configuration
        sshClient.set_log_channel(__name__ + '.paramiko')

        # try to connect and catch possible problems
        try:
            sshClient.connect(
                hostname=self.host_name,
                port=self.port,
                username=self.user,
                password=self.passwd,
                key_filename=self.private_key_path,
                timeout=timeout,
                # disable usage of SSH agent
                allow_agent=False,
                # disable looking for keys in ~/.ssh
                look_for_keys=False
            )
            sftpConn = sshClient.open_sftp()
        # credentials invalid
        except paramiko.AuthenticationException as exc:
            # log the traceback for possible debugging
            self._loggerObj.exception('login exception:')

            # report our custom exception so that upper layers do not tie to
            # the underlying implementation
            raise PermissionError('Invalid credentials')

        # other errors (i.e. protocol or connection errors)
        except Exception as exc:
            # log the traceback for possible debugging
            self._loggerObj.exception('login exception:')

            # report our custom exception so that upper layers do not tie to
            # the underlying implementation
            raise ConnectionError(str(exc))

        self._sshClient = sshClient
        self._sftpConn = sftpConn
    # login()

    def logoff(self):
        """
        Close connection to target system. This function is not expected to
        raise any exception by the library.

        Args:
            None

        Returns:
            None

        Raises:
            None
        """
        # no connection active: nothing to do
        if self._sshClient is None:
            self._loggerObj.warn('logoff called but no connection active: '
                                 'ignoring')
            return

        # according to paramiko no exception can be raised while closing a
        # connection
        self._loggerObj.debug('closing connection to %s', self.host_name)
        self._sftpConn.close()
        self._sftpConn = None
        self._sshClient.close()
        self._sshClient = None
    # logoff()

    def pathExists(self, check_path):
        """
        Verifies if a given path exists on system

        Args:
            check_path: string path

        Returns:
            True if path exists, False otherwise

        Raises:
            IOError: in case path cannot be opened
        """
        # connection not active: fail operation
        if self._sshClient is None:
            raise IOError('Not connected')

        # try to open a file descriptor to file
        try:
            fileFd = self._sftpConn.file(check_path, 'r')
        # not found exception raised: path does not exist
        except FileNotFoundError as exc:
            return False

        # close filehandle
        fileFd.close()

        return True
    # pathExists()

    def pushFile(self, file_path, file_content, file_append=False,
                 file_perms=None):
        """
        Push a file to the target system, optionally appending to the
        existing's file if append is True.

        Args:
            file_path: file path on target system
            file_content: content to be pushed
            file_append: if True tries to append to the end of an existing's
                         file, otherwise creates or overwrites it
            file_perms: integer containing the permission bits (as defined by
                   os.chmod), if None then no chmod is performed on file

        Returns:
            None

        Raises:
            IOError: if not connected or failed to write or set permissions
            ValueError: if permission is in wrong format
        """
        # connection not active: fail operation
        if self._sshClient is None:
            raise IOError('Not connected')

        # convert mode to file object style
        if file_append is True:
            mode = 'a'
        else:
            mode = 'w'

        # content type is not bytes: convert (this might raise
        # UnicodeDecodeError or ValueError)
        if not isinstance(file_content, bytes):
            file_content = bytes(file_content)

        self._loggerObj.debug(
            "pushFile: file_path='%s' append='%s' perms='%s'",
            file_path, file_append, file_perms
        )

        # permissions specified: perform sanity check
        if file_perms is not None:
            try:
                # make sure it's an integer
                file_perms = int(file_perms)
                # exception is raised in case number is out of range
                check_perms = stat.S_IMODE(file_perms)
                # number might be within range but stat had to convert, so
                # in order to avoid inconsistency we also fail in that case
                assert check_perms == file_perms
            except Exception as exc:
                self._loggerObj.exception('pushFile file_perms exception:')
                raise ValueError('Wrong permission format')

        # open a file descriptor and write content (can raise IOError)
        fileFd = self._sftpConn.file(file_path, mode)
        fileFd.write(file_content)
        fileFd.close()

        # permissions specified: apply them
        if file_perms is not None:
            self._sftpConn.chmod(file_path, file_perms)

    # pushFile()

    def pullFile(self, file_path):
        """
        Pull the content of a file from the target system

        Args:
            file_path: string path to file

        Returns:
            file content of type 'bytes'

        Raises:
            FileNotFoundError: if file does not exist
            IOError: if file cannot be read or connection not active
        """
        # connection not active: fail operation
        if self._sshClient is None:
            raise IOError('Not connected')

        # open a file descriptor and read file content
        # the code below can raise IOError or FileNotFoundError
        fileFd = self._sftpConn.file(file_path, 'r')
        content = fileFd.read()
        fileFd.close()

        return content
    # pullFile()

    def openShell(self, chroot_dir=None, shell_path=None):
        """
        Open an interactive shell and return an expect-like object. Optionally
        accepts a directory to perform chroot.

        Args:
            chroot_dir: directory to perform chroot
            shell_path: path where shell is located (defaults to /bin/sh)

        Returns:
            SshShell object

        Raises:
            IOError: if session cannot be opened
            SshClientError: if shell cannot be started
        """
        # connection not active: fail operation
        if self._sshClient is None:
            raise IOError('Not connected')

        # chroot directory does not exist: abort
        if chroot_dir and not self.pathExists(chroot_dir):
            raise FileNotFoundError(
                'Chroot dir {} does not exist'.format(chroot_dir)
            )

        # shell not specified: use default
        if shell_path is None:
            shell_path = '/bin/sh'
        # shell specified does not exist: cannot continue
        elif not self.pathExists(shell_path):
            raise FileNotFoundError(
                'Shell {} does not exist'.format(shell_path)
            )

        # open a new session to be used to run the shell process
        try:
            channel = self._sshClient.get_transport().open_session()
        except paramiko.SSHException as exc:
            self._loggerObj.exception('openShell open_session exception:')
            raise IOError('Failed to open shell: {}'.format(str(exc)))

        # term dumb is important to avoid escape sequences
        # width is important to not truncate long command lines
        channel.get_pty(term='dumb', width=10000)
        # put stdout and stderr in same stream
        channel.set_combine_stderr(True)

        # use -s to make the shell read from stdin
        shell_cmd = '{} -s'.format(shell_path)
        # directory specified: chroot to it
        if chroot_dir:
            shell_cmd = 'chroot %s %s' % (chroot_dir, shell_cmd)
        # start the shell command
        try:
            channel.exec_command(shell_cmd)
        except paramiko.SSHException as exc:
            # log the exception for debugging and raise our own to decouple
            # user from implementation detail
            self._loggerObj.exception('login exception:')
            raise SshClientError('Failed to start shell: {}'.format(str(exc)))

        return SshShell(channel)
    # openShell()

# SSHClient
