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
# pylint: disable=too-few-public-methods
#
# IMPORTS
#
import time
import select
import subprocess

from tessia_baselib.common.logger import getLogger

#
# CONSTANTS AND DEFINITONS
#
STATUS = ['ok', 'error']

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
        self._logger = getLogger(__name__)

        # create new s3270 process and connects to its pipes
        self._s3270 = subprocess.Popen(
            [
                's3270',
                '-model',
                '3278-4',
            ],
            bufsize=1,
            universal_newlines=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    # __init__()

    def _read(self, timeout):
        """
        Perform low level reading from s3270 stdout. This is intended to be
        used internally only.

        Args:
            timeout: how many seconds to wait for an output

        Returns:
            tuple (status, output)

        Raises:
            TimeoutError: if receiving output reaches timeout specified or
                          there is no content to read
        """
        # poll_timeout is defined in miliseconds
        poll_timeout = timeout * 1000
        # define the timeout limit
        timeout = time.time() + timeout

        # buffer for content read
        output = ""
        output_line = ""

        # set poll object to wait for content on stdout before try to read
        poll_obj = select.poll()
        # register stdout descriptor for pending I/O event
        # POLLIN means wait for data to read
        poll_obj.register(self._s3270.stdout, select.POLLIN)
        # poll wait for data on stdout 'poll_timeout' miliseconds before return
        poll_output = poll_obj.poll(poll_timeout)
        # when content is available, 'poll_output' list is filled up with
        # '(fd, event)'
        # fd is the STDOUT file descriptor, and event is a bitmask with bits
        # set for the reported events for that descriptor, in our case, POLLIN.
        # Otherwhise, 'poll_output' will be an empty list.
        if poll_output:
            # loop until we read all the data from stdout or timeout reached
            while True:
                # read line by line from stdout
                output_line = self._s3270.stdout.readline().rstrip('\n')
                output += output_line+'\n'

                # all data received or EOF: finish operation
                if output_line in STATUS or len(output_line) == 0:
                    break

                # timeout reached: abort with exception
                if time.time() > timeout:
                    self._logger.debug('content read: %s', output)
                    raise TimeoutError('Timeout while reading output')
        else:
            raise TimeoutError('No content to read')

        # remove trailing newline as it is added by logger later
        self._logger.info(output.rstrip('\n'))

        # return status and output
        return (output_line, output)
    # _read()

    def _write(self, cmd, timeout):
        """
        Perform low level writing to s3270 stdin. This is intended to be used
        internally only.

        Args:
            cmd: s3270 command
            timeout: how many seconds to wait for an output

        Returns:
            None

        Raises:
            TimeoutError: if stdin is not available
        """
        # remove trailing newline as it is added by logger later
        self._logger.info('s3270 console: %s', cmd.rstrip('\n'))

        # poll_timeout is defined in miliseconds
        poll_timeout = timeout * 1000

        # set poll object to wait for stdin to be read before write to it
        poll_obj = select.poll()
        # register stdin descriptor for I/O event
        # POLLOUT means wait for data to read
        poll_obj.register(self._s3270.stdin, select.POLLOUT)
        # poll wait for stdin for 'poll_timeout' miliseconds before return
        poll_output = poll_obj.poll(poll_timeout)
        # when stdin is available, 'poll_output' list is filled up with
        # '(fd, event)'
        # fd is the STDIN file descriptor, and event is a bitmask with bits
        # set for the reported events for that descriptor, in our case,
        # POLLOUT.
        # Otherwhise, 'poll_output' will be an empty list.
        if poll_output:
            # write command to s3270 stdin
            self._s3270.stdin.write(cmd+"\n")
        else:
            self._logger.debug('stdin not available')
            raise TimeoutError('Could not write on stdin')
    # _write()

    def run(self, cmd, timeout=120):
        """
        Execute a command and wait 'timeout' seconds for the output. This
        method is the entry point to be consumed by users.

        Args:
            cmd: s3270 command
            timeout: how many seconds to wait for an output to complete

        Returns:
            tuple (status, output)

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

# S3270PipeConnector
