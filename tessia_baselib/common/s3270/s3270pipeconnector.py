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
S3270 Pipe connector class
"""
# pylint: disable=redefined-variable-type
#
# IMPORTS
#
import time
import select
import subprocess
from os import read

from tessia_baselib.common.logger import get_logger

#
# CONSTANTS AND DEFINITONS
#
# Possible status messages from s3270 terminal
STATUS = [b'ok', b'error']
# Maximum s3270 data line size
ROW_SIZE = 87

#
# CODE
#
class S3270PipeConnector(object):
    """
    This class encapsulates the reading from and writing to an s3270 process
    pipe. The objective is to be a connector to the s3270 process.
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
        self._logger = get_logger(__name__)

        # create new s3270 process and connects to its pipes
        self._s3270 = subprocess.Popen(
            [
                's3270',
                '-model',
                '3278-4',
            ],
            bufsize=0,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )

        # set poll object to wait for content on stdin/stdout
        self._poller = select.epoll()
        self._stdout_fd = self._s3270.stdout.fileno()
        self._stdin_fd = self._s3270.stdin.fileno()
        # register stdout descriptor for pending I/O event
        # EPOLLIN means available for read
        self._poller.register(self._stdout_fd, select.EPOLLIN)
        # register stdin descriptor for I/O event
        # EPOLLOUT means available for write
        self._poller.register(self._stdin_fd, select.EPOLLOUT)
    # __init__()

    def _read(self, timeout=120):
        """
        Perform low level reading from s3270 stdout. This is intended to be
        used internally only.

        Args:
            timeout (int): how many seconds to wait for an output

        Returns:
            str: last line of s3270 terminal with status message
            str: whole output content from s3270 terminal

        Raises:
            TimeoutError: if while receiving output we reaches timeout
                          specified
        """
        # define the timeout limit
        timeout = time.time() + timeout

        # buffer for content read
        output = b''
        buffer_read = b''

        # poll wait for data on stdout 1 second before return.
        # when content is available, 'events' list is filled up with
        # '(fd, event)' of all registered fd.
        # here we are looking for STDOUT file descriptor, and event with a
        # bitmask of bits set for the reported events for that descriptor,
        # in our case, EPOLLIN.
        # Otherwhise, 'events' will be an empty list.
        # loop until we read all the data from stdout or timeout reached
        while True:
            events = self._poller.poll(1)
            for fileno, _ in events:
                if fileno == self._stdout_fd:
                    # read 'ROW_SIZE' bytes from stdout
                    buffer_read += read(self._stdout_fd, ROW_SIZE)

                # timeout reached: abort with exception
                if time.time() > timeout:
                    self._logger.debug('content read: %s', output)
                    raise TimeoutError('Timeout while reading output')

                # if we do not have the full line, keep reading
                if buffer_read.find(b'\n') < 0:
                    continue

            # append buffer to the output
            output += buffer_read

            # 'ok/error' found: finish operation
            if output.rsplit() and output.rsplit()[-1] in STATUS:
                break

            # more content to read, clean buffer
            buffer_read = b''

            # timeout reached: abort with exception
            if time.time() > timeout:
                self._logger.debug('content read: %s', output)
                raise TimeoutError('Timeout while reading output')

        # convert output to text
        output = output.decode()

        # remove trailing newline as it is added by logger later
        self._logger.info(output.rstrip('\n'))

        # return status and output
        return (output.rsplit()[-1], output)
    # _read()

    def _write(self, cmd, timeout=120):
        """
        Perform low level writing to s3270 stdin. This is intended to be used
        internally only.

        Args:
            cmd (str): s3270 command
            timeout (int): how many seconds to wait for stdin to be ready

        Returns:
            None

        Raises:
            TimeoutError: if stdin is not available
        """
        # remove trailing newline as it is added by logger later
        self._logger.info('s3270 console: %s', cmd.rstrip('\n'))

        # command arrives without newline control character
        cmd = cmd+'\n'

        # define the timeout limit
        timeout = time.time() + timeout

        # poll wait for data on stdin 1 second before return.
        # when content is available, 'events' list is filled up with
        # '(fd, event)' of all registered fd.
        # here we are looking for STDIN file descriptor, and event with a
        # bitmask of bits set for the reported events for that descriptor,
        # in our case, EPOLLOUT.
        # Otherwhise, 'events' will be an empty list.
        # loop until we read all the data from stdout or timeout reached
        done = 0
        while not done:
            events = self._poller.poll(1)
            for fileno, _ in events:
                if fileno == self._stdin_fd:
                    self._s3270.stdin.write(cmd.encode('utf-8'))
                    done = 1

                # timeout reached: abort with exception
                if time.time() > timeout:
                    self._logger.debug('stdin not available')
                    raise TimeoutError('Could not write on stdin')
    # _write()

    def quit(self, timeout=120):
        """
        Execute a 'Quit' command and return.

        Args:
            None

        Returns:
            None

        Raises:
            None
        """
        # write command to s3270 stdin
        self._write('Quit', timeout)

        # clean up process
        self.terminate()

        # remove trailing newline as it is added by logger later
        self._logger.info('prompt: Quiting!')
    # quit()

    def run(self, cmd, timeout=120):
        """
        Execute a command and wait 'timeout' seconds for the output. This
        method is the entry point to be consumed by users.

        Args:
            cmd (str): s3270 command
            timeout (int): how many seconds to wait for an output to complete

        Returns:
            str: last line of s3270 terminal with status message
            str: whole output content from s3270 terminal

        Raises:
            None
        """
        # write command to s3270 stdin
        self._write(cmd, timeout)
        # read status and output from stdout
        (status, output) = self._read(timeout)

        # remove trailing newline as it is added by logger later
        self._logger.info('prompt: %s', cmd)

        return (status, output)
    # run()

    def terminate(self, timeout=120):
        """
        Terminate process execution and clean up object.

        Args:
            None

        Returns:
            None

        Raises:
            None
        """
        # communicate wait for the process to end
        try:
            self._s3270.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            # kill the process otherwise
            self._s3270.kill()
            # and try to communicate again to clen up defunct
            self._s3270.communicate(timeout=timeout)

        # clean up object
        self._s3270 = None
    # terminate()

# S3270PipeConnector
