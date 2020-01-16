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
Implementation of a shell object wrapping a ssh connection
"""

#
# IMPORTS
#
from tessia.baselib.common.logger import get_logger
from tessia.baselib.common.ssh.exceptions import SshShellError
from uuid import uuid4

import select
import socket
import time

#
# CONSTANTS AND DEFINITONS
#
ENCODING = 'utf-8'

#
# CODE
#
class SshShell:
    """
    This class encapsulates the reading from and writing to a file
    object/socket and performing expect work to provide a shell object
    which represents an interactive shell session.
    """
    def __init__(self, socket_obj):
        """
        Receives a socket to use for communication with the shell and prepares
        the expect configuration.

        Args:
            socket_obj (socket): socket object for reading and writing

        Raises:
            None
        """
        # main logger to report issues
        self._main_logger = get_logger(__name__)

        # logger to report all communication content. By default we don't want
        # it to dump a lot of messages if user didn't choose explicity to get
        # it, so we set propagate as false to assure that.
        self._console_logger = get_logger(__name__ + '.console', False)

        # store socket object
        self.socket = socket_obj

        # do an initial read to prevent a problem where we issue the command
        # too fast and the remote side shows the prompt later beneath it,
        # causing our expect algorithm to fail.
        self.prompt = '\n'
        self._write('\n')
        self._read()

        # the main problem with doing 'expect work' is to detect when the
        # output is really over. Usually this is done by waiting the prompt but
        # this can generate false positives. In order to avoid that and
        # simplify output parsing we set the prompt to a unique identifier so
        # that we make sure that once it is found it means the output has
        # finished.
        self.prompt = str(uuid4())

        # commands to prepare the shell environment
        initial_cmds = [
            # use variable expansion to prevent the first _read() from matching
            # the command line instead of the prompt
            'prompt_end=":"; export PS1="{}$prompt_end"; unset prompt_end'
            .format(self.prompt),
        ]

        self._write(';'.join(initial_cmds) + '\n')
        self.prompt += ':'

        # perform a first read to consume the expect setup above
        self._read()

        # pager variable is to prevent systemd commands from calling some pager
        # which would cause output to hang
        status, output = self.run(
            'export SYSTEMD_PAGER=; export LC_ALL=en_US.UTF-8; locale charmap')

        # locale command worked: check its output
        if status == 0:
            charmap = output.strip()
            # charmap is utf-8 like expected: return
            if charmap == 'UTF-8':
                return

            self._main_logger.warning('Charmap file %s is not UTF-8',
                                      charmap)
        # locale command failed: log warning
        else:
            self._main_logger.warning('Could not determine charmap')

        self._main_logger.warning(
            'Data in this ssh channel is encoded and decoded in UTF-8, '
            'but the shell locale seems to be using a different encoding.'
        )

    # __init__()

    def _read(self, timeout=120, cmd_echo=None):
        """
        Perform low level reading from socket. This is intended to be used
        internally only.

        Args:
            timeout (int): how many seconds to wait for input
            cmd_echo (str): initial command to remove its echo from output

        Returns:
            str: with content read from socket

        Raises:
            SshShellError: if incorrect unicode character was received
            TimeoutError: if timeout is reached and no content read
        """
        # define the timeout limit
        timeout = time.time() + timeout

        # buffer for content read
        output = ""

        # buffer for parts of distorted unicode text
        byte_buffer = b""

        # read from socket until prompt is found or timeout reaches
        while True:
            # wait during 0.1 seconds for socket to be available for reading
            r_list, _, _ = select.select([self.socket], [], [], 0.1)
            # socket ready for reading: read 1024 bytes to buffer
            if r_list:
                try:
                    # assume data we receive is in utf-8 and decode it as such
                    output += str(self.socket.recv(1024), ENCODING)
                # ignore timeout and keep trying until our timeout is reached
                except socket.timeout:
                    self._main_logger.warning(
                        'Timeout while performing socket.recv'
                    )
                except UnicodeDecodeError as error:
                    # avoid retrying to decode the first distorted part
                    if not byte_buffer:
                        byte_buffer = error.args[1]
                        continue

                    byte_buffer += error.args[1]
                    try:
                        output += byte_buffer.decode(ENCODING)
                    # decoding failed: try to read more bytes
                    except UnicodeDecodeError:
                        continue
                    # multi-byte character was decoded: reset buffer
                    byte_buffer = b""

                else:
                    # decoding worked but buffer had character: output contains
                    # invalid character encoding
                    if byte_buffer:
                        raise SshShellError(
                            'Incorrect unicode character was received')

            # try to match the prompt in the buffer
            index = output.find(self.prompt)

            # we got the prompt: read finished
            if index > -1:
                # remove command prompt and any garbage after it
                output = output[:index]
                break
            # timeout reached: abort and raise exception
            if time.time() > timeout:
                raise TimeoutError('Timeout waiting for command output')

        output = output.replace('\r\n', '\n')

        # command echo found in output: remove it
        # There might be escape chars in the beginning of the line,
        # so we must make sure that we find the correct position of the
        # command echo.
        if cmd_echo is not None:
            cmd_echo_offset = output.find(cmd_echo)
            if cmd_echo_offset != -1:
                output = output[cmd_echo_offset + len(cmd_echo):]

        # remove trailing newline as it is added by logger later
        self._console_logger.info(output.rstrip('\n'))

        return output
    # _read()

    def _write(self, content, timeout=60):
        """
        Perform low level writing to socket. This is intended to be used
        internally only.

        Args:
            timeout (int): how many seconds to wait for operation to complete
            content (str): it will be encoded in utf-8 prior to writing

        Raises:
            TimeoutError: if timeout is reached and write did not complete
        """
        # remove trailing newline as it is added by logger later
        self._console_logger.info('prompt: %s', content.rstrip('\n'))

        # define the timeout limit
        timeout = time.time() + timeout

        # ensure content is in bytes so we use the correct length
        content = content.encode(ENCODING)

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

        Raises:
            None
        """
        try:
            self.socket.close()
        except Exception:
            pass
    # close()

    def run(self, cmd, timeout=120, ignore_ret=False):
        """
        Execute a command and wait timeout seconds for the output. This method
        is the entry point to be consumed by users.

        Args:
            cmd (str): command
            timeout (int): how many seconds to wait for output to complete
            ignore_ret (bool): if the exit_code and output should be ignored


        Returns:
            tuple: (exit_code, output)

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

        # send command and ignore return values
        if ignore_ret:
            return 0, ""

        # read the output from command
        output = self._read(timeout, cmd)

        # get exit status
        status_cmd = 'echo $?\n'
        self._write(status_cmd)
        status = self._read(timeout, status_cmd)
        try:
            exit_code = int(status)
        # in case of error raise our own exception to not expose internal
        # implementation
        except (TypeError, ValueError) as exc:
            raise SshShellError(
                'Failed to parse command return status: {}'.format(str(exc))
            )

        return exit_code, output
    # run()

# SshShell
