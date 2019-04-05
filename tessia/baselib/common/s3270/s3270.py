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
S3270 module
"""
#
# IMPORTS
#
import time

from tessia.baselib.common.logger import get_logger
from tessia.baselib.common.s3270.exceptions import S3270StatusError
from tessia.baselib.common.s3270.s3270pipeconnector import S3270PipeConnector
#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
class S3270:
    """
    This class provides an implementation of s3270 commands.
    Implementation detail: we might want to use different connector in the
    future so we catch, log and rethrow the exceptions raised by the
    connector in order to have a stable interface with the upper layers.
    """

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

        # connection parameters
        self.host_name = None

        # create a new s3270 object
        self._s3270 = S3270PipeConnector()
    # __init__()

    def ascii(self, param=None, timeout=60):
        """
        Send an Ascii command to s3270

        Args:
            param (list): row,col,rows,cols
                          row,col,length
                          length
            timeout (int): how many seconds to wait for action to complete

        Returns:
            output: output of run command

        Raises:
            TimeoutError: if we have a timeout on connector
            S3270StatusError: if protocol error occurred
        """
        cmd = "Ascii"
        # add parameters to Ascii command
        if param is not None and param:
            cmd = "Ascii("
            for item in param:
                cmd += str(item)+","
            # remove last ',' and add ')'
            cmd = cmd[:-1]+")"

        try:
            (status, output) = self._s3270.run(cmd, timeout)
        except TimeoutError:
            self._logger.exception('Timeout while executing Ascii:')
            raise

        if 'ok' not in status:
            raise S3270StatusError('Error while sending Ascii command')

        return output
    # ascii()

    def clear(self, timeout=60):
        """
        Send a Clear command to s3270

        Args:
            timeout (int): how many seconds to wait for action to complete

        Returns:
            output: output of run command

        Raises:
            TimeoutError: if we have a timeout on connector
            S3270StatusError: if protocol error occurred
        """
        try:
            (status, output) = self._s3270.run('Clear', timeout)
        except TimeoutError:
            self._logger.exception('Timeout while executing Clear:')
            raise

        if 'ok' not in status:
            raise S3270StatusError('Error while sending Clear command')

        return output
    # clear()

    def connect(self, host_name, timeout=60):
        """
        Stablishes a connection to the target system

        Args:
            host_name (str): target hostname
            timeout (int): how many seconds to wait for action to complete

        Returns:
            output: output of run command

        Raises:
            TimeoutError: if we have a timeout on connector
            S3270StatusError: if protocol error occurred
        """
        # save hostname for later use
        self.host_name = host_name

        # define the timeout limit
        timeout = time.time() + timeout

        # define status and output
        status = ""
        output = ""

        # loop until connection stablished or timeout
        while True:
            try:
                # s3270 uses connect() C function to connect to a socket
                # this function uses system parameters to define timeout
                # our connect timeout needs to be longer than system timeout
                # so we are able to read s3270 stdout. If we cannot read
                # stdout, it means the host is taking so long to answer, so
                # we decided to raise an exception and do not worry about
                # possible inconsistent output on s3270 stdout
                (status, output) = self._s3270.run('Connect('+host_name+')',
                                                   180)
            except TimeoutError:
                self._logger.exception(
                    'Host %s is taking too long to answer: ', host_name)
                raise TimeoutError('Host is taking too long to answer')

            if status:
                if 'No address associated with hostname' in output:
                    raise S3270StatusError('No address associated with '
                                           'hostname '+host_name)
                if 'error' in status:
                    raise S3270StatusError(
                        'Error while sending Connect command'
                    )
                if 'ok' in status:
                    break

            if time.time() > timeout:
                raise TimeoutError('Timeout while connecting to '+host_name)

        return output
    # connect()

    def disconnect(self, timeout=60):
        """
        Send a Disconnect command to s3270

        Args:
            timeout (int): how many seconds to wait for action to complete

        Returns:
            output: output of run command

        Raises:
            TimeoutError: if we have a timeout on connector
            S3270StatusError: if protocol error occurred
        """
        try:
            (status, output) = self._s3270.run('Disconnect', timeout)
        except TimeoutError:
            self._logger.exception('Timeout while executing Disconnect:')
            raise

        if 'ok' not in status:
            raise S3270StatusError('Error while sending Disconnect command')

        return output
    # disconnect()

    def enter(self, timeout=60):
        """
        Send an Enter command to s3270

        Args:
            timeout (int): how many seconds to wait for action to complete

        Returns:
            output: output of run command

        Raises:
            TimeoutError: if we have a timeout on connector
            S3270StatusError: if protocol error occurred
        """
        try:
            (status, output) = self._s3270.run('Enter', timeout)
        except TimeoutError:
            self._logger.exception('Timeout while executing Enter:')
            raise

        if 'ok' not in status:
            raise S3270StatusError('Error while sending Enter command')

        return output
    # enter()

    def execute(self, cmd, timeout=60):
        """
        Execute a command in a shell

        Args:
            cmd (str): command to be executed
            timeout (int): how many seconds to wait for action to complete

        Returns:
            output: output of run command

        Raises:
            TimeoutError: if we have a timeout on connector
            S3270StatusError: if protocol error occurred
        """
        try:
            (status, output) = self._s3270.run('Execute('+cmd+')', timeout)
        except TimeoutError:
            self._logger.exception('Timeout while executing Execute:')
            raise

        if 'ok' not in status:
            raise S3270StatusError('Failed to execute '+cmd+' using s3270')

        return output
    # execute()

    def query(self, attr="", timeout=60):
        """
        Send a Query command to s3270

        Args:
            attr (str): attribute to be queried
            timeout (int): how many seconds to wait for action to complete

        Returns:
            output: output of run command

        Raises:
            TimeoutError: if we have a timeout on connector
            S3270StatusError: if protocol error occurred
        """
        if not attr:
            try:
                (status, output) = self._s3270.run('Query("Host")', timeout)
            except TimeoutError:
                self._logger.exception('Timeout while executing Query:')
                raise
        else:
            try:
                (status, output) = self._s3270.run('Query("'+attr+'")',
                                                   timeout)
            except TimeoutError:
                self._logger.exception('Timeout while executing Query:')
                raise

        if 'ok' not in status:
            raise S3270StatusError('Error while sending Query command')

        return output
    # query()

    def quit(self, timeout=60):
        """
        Send a Quit command to s3270

        Args:
            timeout (int): how many seconds to wait for action to complete

        Raises:
            TimeoutError: if we have a timeout on connector
            S3270StatusError: if protocol error occurred
        """
        try:
            self._s3270.quit(timeout)
        except TimeoutError:
            self._logger.exception('Timeout while executing Quit:')
            raise

        # clean object
        self.host_name = None
        self._s3270 = None
    # quit()

    def snap(self, cmd="", timeout=60):
        """
        Send a Snap command to s3270 with 'cmd' content

        Args:
            cmd (str): content to be sent to Snap
            timeout (int): how many seconds to wait for action to complete

        Returns:
            output: output of run command

        Raises:
            TimeoutError: if we have a timeout on connector
            S3270StatusError: if protocol error occurred
        """
        if not cmd:
            try:
                (status, output) = self._s3270.run('Snap', timeout)
            except TimeoutError:
                self._logger.exception('Timeout while executing Snap:')
                raise
        else:
            try:
                (status, output) = self._s3270.run('Snap("'+cmd+'")', timeout)
            except TimeoutError:
                self._logger.exception('Timeout while executing Snap:')
                raise

        if 'ok' not in status:
            raise S3270StatusError('Error while sending Snap command')

        return output
    # snap()

    def string(self, str_content, timeout=60, hide=False):
        """
        Send a String command to s3270 with 'string' content

        Args:
            str_content (str): content to be sent to String
            timeout (int): how many seconds to wait for action to complete
            hide (bool): whether the command is sensitive (i.e. password) and
                         should be suppressed in the log

        Returns:
            output: output of run command

        Raises:
            TimeoutError: if we have a timeout on connector
            S3270StatusError: if protocol error occurred
        """
        try:
            (status, output) = self._s3270.run(
                'String("{}")'.format(str_content), timeout=timeout, hide=hide)
        except TimeoutError:
            self._logger.exception('Timeout while executing String:')
            raise

        if 'ok' not in status:
            raise S3270StatusError('Error while sending String command')

        return output
    # string()

    def transfer(self, local_path, remote_path, direction='send', timeout=180,
                 mode='binary', recfm='fixed', **extra_params):
        """
        Send a file to host/receive a file from host

        Args:
            local_path (str): file name on local filesystem
            remote_path (str): file name on target host
            direction (str): send (local -> host), receive (host -> local)
            timeout (int): how many seconds to wait for action to complete
            mode (str): binary or ascii
            recfm (str): fixed or variable
            extra_params (dict): additional option=value parameters accepted by
                                 s3270

        Returns:
            output: output of transfer command

        Raises:
            TimeoutError: if we have a timeout on connector
            S3270StatusError: if protocol error occurred
            ValueError: if an invalid value is specified for an option
        """
        # sanity checks
        if direction.lower() not in ('send', 'receive'):
            raise ValueError("Invalid direction '{}'".format(direction))
        if mode.lower() not in ('ascii', 'binary'):
            raise ValueError("Invalid mode '{}'".format(mode))
        if recfm.lower() not in ('fixed', 'variable'):
            raise ValueError("Invalid recfm option '{}'".format(recfm))

        params_str = (
            'Direction={}, "LocalFile={}", "HostFile={}", Mode={}, Recfm={}, '
            'Host=vm'.format(direction, local_path, remote_path, mode, recfm)
        )
        for key, value in extra_params.items():
            params_str += ', {}="{}"'.format(key, value)
        self._logger.debug('calling Transfer with params: %s', params_str)

        status, output = self._s3270.run(
            'Transfer({})'.format(params_str), timeout=timeout)

        if 'ok' not in status:
            raise S3270StatusError(
                'Failed to execute Transfer command', output)

        return output
    # transfer()
# S3270
