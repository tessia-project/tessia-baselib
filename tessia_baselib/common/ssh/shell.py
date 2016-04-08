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
from tessia_baselib.common.ssh.exceptions import SshShellError
from uuid import uuid4

import select
import socket
import time

#
# CONSTANTS AND DEFINITONS
#

#
# CODE
#
class SshShell(object):
    """
    This class encapsulates the reading from and writing to a file object/socket
    and perform expect work to provide a shell object which represents an
    interactive shell session.
    """
    def __init__(self, socketObj):
        """
        Receives a socket to use for communication with the shell and prepares
        the expect configuration.

        Args:
            socket: socket object for reading and writing

        Returns:
            None

        Raises:
            None
        """
        # main logger to report issues
        self._mainLogger = getLogger(__name__)

        # logger to report all communication content. By default we don't want
        # it to dump a lot of messages if user didn't choose explicity to get
        # it, so we set propagate as false to assure that.
        self._consoleLogger = getLogger(__name__ + '.console', False)

        # store socket object
        self.socket = socketObj

        # the main problem with doing 'expect work' is to detect when the output
        # is really over. Usually this is done by waiting the prompt but this
        # can generate false positives. In order to avoid that and simplify
        # output parsing we set the prompt to a unique identifier so that we
        # make sure that once it is found it means the output has finished.
        self.prompt = str(uuid4())

        # commands to prepare the shell environment
        initial_cmds = [
            # to avoid problems with converting the output from the type bytes
            # to string (and unicode) we force the use of ascii output by
            # setting the locale to C
            'export LC_ALL=C',
            # use variable expansion to prevent the first _read() from matching
            # the command line instead of the prompt
            'prompt_end=":"; export PS1="{}$prompt_end"; unset prompt_end'
            .format(self.prompt),
        ]

        self._write(';'.join(initial_cmds) + '\n')
        self.prompt += ':'

        # perform a first read to consume the expect setup above
        self._read()
    # __init__()

    def _read(self, timeout=120, cmd_echo=None):
        """
        Perform low level reading from socket. This is intended to be used
        internally only.

        Args:
            timeout: how many seconds to wait for input
            cmd_echo: initial command string to remove its echo from output

        Returns:
            string with content read from socket

        Raises:
            TimeoutError: if timeout is reached and no content read
        """
        # define the timeout limit
        timeout = time.time() + timeout

        # buffer for content read
        output = ""

        # read from socket until prompt is found or timeout reaches
        while True:
            # wait during 0.1 seconds for socket to be available for reading
            r_list, _, _ = select.select([self.socket], [], [], 0.1)
            # socket ready for reading: read 1024 bytes to buffer
            if len(r_list) > 0:
                try:
                    # we assured output is ascii by setting LC_ALL=C before so
                    # it's safe to convert the type bytes returned here to
                    # string using ascii decoding.
                    output += str(self.socket.recv(1024), 'ascii')
                # ignore timeout and keep trying until our timeout is reached
                except socket.timeout:
                    self._mainLogger.warning(
                        'Timeout while performing socket.recv'
                    )

            # try to match the prompt in the buffer
            index = output.find(self.prompt)

            # we got the prompt: read finished
            if index > -1:
                # remove command prompt and any garbage after it
                output = output[:index]
                break
            # timeout reached: abort and raise exception
            elif time.time() > timeout:
                raise TimeoutError('Timeout waiting for command output')

        output = output.replace('\r\n', '\n')

        # command echo found in output: remove it
        if cmd_echo is not None and output[0:len(cmd_echo)] == cmd_echo:
            output = output[len(cmd_echo):]

        # remove trailing newline as it is added by logger later
        self._consoleLogger.info(output.rstrip('\n'))

        return output
    # _read()

    def _write(self, content, timeout=60):
        """
        Perform low level writing to socket. This is intended to be used
        internally only.

        Args:
            timeout: how many seconds to wait for operation to complete

        Returns:
            None

        Raises:
            TimeoutError: if timeout is reached and write did not complete
        """
        # remove trailing newline as it is added by logger later
        self._consoleLogger.info('prompt: %s', content.rstrip('\n'))

        # define the timeout limit
        timeout = time.time() + timeout

        # size of buffer we need to write
        size = len(content)

        # control variable to decide when all content was written
        counter = 0

        # loop until we wrote all the data from buffer or timeout reached
        while True:
            # socket ready for writing: try to write as much as possible
            # here we use a paramiko specific function send_ready() so in case
            # of usage with other sockets try to use select.select instead
            if self.socket.send_ready():
                # add amount of bytes written to counter
                counter += self.socket.send(content[counter:])
            # timeout reached: abort with exception
            elif time.time() > timeout:
                raise TimeoutError('Timeout waiting to send command')
            # all data sent: finish operation
            if counter >= size:
                break
    # _write()

    def close(self):
        """
        Close the socket. No more operations are possible.

        Args:
            None

        Returns:
            None

        Raises:
            None
        """
        self.socket.close()
    # close()

    def run(self, cmd, timeout=120):
        """
        Execute a command and wait timeout seconds for the output. This method
        is the entry point to be consumed by users.

        Args:
            cmd: string command
            timeout: how many seconds to wait for output to complete

        Returns:
            tuple (exit_code, output)

        Raises:
            SshShellError: if it fails to parse the command exit code
            TimeoutError: if sending command or receiving output reaches
                          timeout specified
        """
        # discard any previous garbage
        self._write('\n')
        self._read(timeout)

        # make sure we have a trailing breakline so that the shell executes the
        # command
        if not cmd.endswith('\n'):
            cmd += '\n'

        # send command through socket
        self._write(cmd)
        # read the output from command
        output = self._read(timeout, cmd)

        # get exit status
        status_cmd = 'echo $?\n'
        self._write(status_cmd)
        status = self._read(timeout, status_cmd)
        try:
            status = int(status)
        # in case of error raise our own exception to not expose internal
        # implementation
        except (TypeError, ValueError) as exc:
            raise SshShellError(
                'Failed to parse command return status: {}'.format(str(exc))
            )

        return status, output
    # run()

# SshShell
