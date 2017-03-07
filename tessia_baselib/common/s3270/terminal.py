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
Terminal module
"""
#
# IMPORTS
#
import time

from tessia_baselib.common.logger import get_logger
from tessia_baselib.common.s3270.exceptions import ZvmMessageError
from tessia_baselib.common.s3270.s3270 import S3270
#
# CONSTANTS AND DEFINITIONS
#
# zVM messages and codes
ZVM_CODES = {
    "RPIMGR042I": "PASSWORD EXPIRED",
    "RPIMGR046T": "User ID access has been revoked.",
    "HCPCFC015E": "Command not valid before LOGON",
    "HCPLGA050E": "LOGON unsuccessful--incorrect userid and/or password",
    "HCPLGA054E": "Already logged on",
    "HCPUSO361E": "LOGOFF/FORCE pending for user",
}


#
# CODE
#
class Terminal(object):
    """
    This class provides an implementation of an s3270 terminal.
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

        # connection parameters
        self.host_name = None

        # create a new s3270 object
        self._s3270 = S3270()
    # __init__()

    @staticmethod
    def _check_output(text):
        """
        Look for zVM error codes into the text and return it when found.

        Args:
            text (str): text to be checked

        Returns:
            str: message corresponding to the code
            None: No error code found

        Raises:
            None
        """
        # check line by line of text
        for line in text.splitlines():
            # check if error message is in the beggining of the line
            if line[1:11] in ZVM_CODES:
                # return error message
                return ZVM_CODES[line[1:11]]
        # return None if no error code was found
        return None
    # _check_output()

    def _check_status(self, output=''):
        """
        Look at CP status area for current status.

        Args:
            output (str): output to be checked

        Returns:
            str: current status in CP status area

        Raises:
            None
        """
        # if an output text is passed as argument, look for status there
        if len(output) > 0:
            status = output[-21:-14]
        else:
            # look at status area
            status = self._s3270.ascii([42, 60, 7])
            # format output to have just the status
            status = self._format_output(status, strip=True).strip()

        # return the current status found
        return status
    # _check_status()

    @staticmethod
    def _format_output(text, strip=False):
        """
        Format the text to remove s3270 tags, s3270 flags,
        status line and blank lines.

        Args:
            text (str): text to be formated
            strip (bool): whether to remove blank lines

        Returns:
            str: formated output

        Raises:
            None
        """
        output = ""

        # check line by line of text
        for line in text.splitlines():
            # remove 'data:' from the beginning
            if line.startswith('data:'):
                line = line[5:]
            # ignore last 2 lines (flags and status)
            elif (
                    line.startswith('U F U') or
                    line.startswith('ok') or
                    line.startswith('L U U')
                ):
                continue
            # remove blank lines when strip is specified
            if strip:
                if line.strip():
                    output += line+'\n'
            else:
                output += line+'\n'
        return output
    # _format_output()

    def _is_connected(self):
        """
        Check if current object is connected to a host by quering the host
        attribute. When there is a connection opened, query will return the
        hostname. When there is not a connection opened, query will return
        an empty string.

        Args:
            None

        Returns:
            bool: True if connected to a host, False otherwise

        Raises:
            None
        """
        # If hostname was not set yet, a connection was not opened.
        if not self.host_name:
            return False

        # query host
        output = self._s3270.query()

        # remove unnecessary data
        output = self._format_output(output, strip=True)

        # check if object has a connection
        if self.host_name in output:
            return True
        return False
    #_is_connected()

    def _is_output_full(self, output=''):
        """
        Look for page full status in CP status area.

        Args:
            output (str): output to be checked
            None

        Returns:
            bool: True if output is full

        Raises:
            None
        """
        # valid status for a full output
        cp_status = [
            "MORE...",
            "HOLDING"
        ]

        # look at status area
        status = self._check_status(output)

        # if output is full return True
        if status in cp_status:
            return True
        return False
    # _is_output_full()

    def _parse_output(self, wait_for='', timeout=60):
        """
        Parse the output looking for 'wait_for'.

        Args:
            wait_for (str): string to stop parsing
            timeout (int): how many seconds to wait for action to complete

        Returns:
            tuple: (str, bool) str: full output until 'wait_for' was found or
                                    timeout occurred
                               bool: True if time expired

        Raises:
            None
        """
        time_expired = False
        output = ""

        if len(wait_for) > 0:
            # variable for wait_for control
            found = False
            # define the timeout limit
            timeout = time.time() + timeout

            # while wait_for not found on current_output
            while not found and not time_expired:
                # read the current information on terminal
                current_output = self._s3270.ascii()
                # remove unnecessary data
                current_output = self._format_output(
                    current_output, strip=True)

                # terminal is full: clear it
                if self._is_output_full(current_output):
                    # append current information to the output
                    output += current_output
                    self._s3270.clear()

                # 'wait_for' found: set variable to stop processing
                if wait_for in current_output:
                    # append current information to the output
                    output += current_output
                    found = True

                # check if we reached a timeout
                if time.time() > timeout:
                    time_expired = True
        else:
            output = self._s3270.ascii()
            output = self._format_output(output, strip=True)

        return (output, time_expired)
    # _parse_output()

    def connect(self, host_name, timeout=60):
        """
        Connects to the hostname provided.

        Args:
            host_name (str): target hostname
            timeout (int): how many seconds to wait for connection

        Returns:
            None

        Raises:
            None
        """
        # check if connection exists and drop it if necessary
        if self._is_connected():
            self._logger.warning(
                "Connection already active:"
                " dropping previous connection"
            )
            self._s3270.disconnect()

        # save hostname for later use
        self.host_name = host_name

        # create a s3270 connection to the host using our s3270 module
        self._s3270.connect(self.host_name, timeout)
    # connect()

    def send_cmd(self, cmd, use_cp=False, wait_for=''):
        """
        Issue a command on zVM.

        Args:
            cmd (str): command to be executed
            use_cp (bool): whether the command should be executed on CP
            wait_for (str): process until wait_for is found

        Returns:
            str: command output

        Raises:
            RuntimeError: if connection to the host was lost
        """
        if not self._is_connected():
            raise RuntimeError('Connection to host lost.')

        # make sure we have a clear screen for output
        self._s3270.clear()
        # put command on input line
        if use_cp:
            self._s3270.string("#cp "+cmd)
        else:
            self._s3270.string(cmd)
        # issue the command
        self._s3270.enter()

        # read output of command issued
        output = self._parse_output(wait_for)

        return output
    # send_cmd()

    def login(self, host_name, user, password, parameters=None, timeout=60):
        """
        Execute a login to the user id using the credentials provided.

        Args:
            host_name (str): target hostname
            user (str): guest user id
            password (str): guest password
            parameters (dict): dictionary with aditional login parameters
            timeout (int): how many seconds to wait for action to complete

        Returns:
            str: output of login

        Raises:
            TimeoutError: if we have a timeout on connector
            S3270StatusError: if protocol error occurred
            ZvmMessageError: if we have a zVM message code
        """
        # setup aditional login parameters
        byuser = ''
        here = ''
        if parameters:
            # check if we will do a logon by
            if parameters.get('byuser'):
                byuser = ' by ' + parameters.get('byuser')
            # check if we will do a logon here
            if parameters.get('here'):
                here = ' here'

        # create an s3270 connection to the host
        self.connect(host_name, timeout)

        # login process
        self._s3270.clear()
        self._s3270.string("l " + user + byuser + here)
        self._s3270.enter()
        self._s3270.string(password)
        self._s3270.enter()

        output = self._s3270.ascii()

        # look for error messages during login
        err_message = self._check_output(self._format_output(output))

        if err_message:
            raise ZvmMessageError(err_message)

        # look for vm or cp read status in CP status area.
        status = self._check_status()

        # try to set the machine on running status
        if status == "CP READ":
            self._s3270.string("begin")
            self._s3270.enter()

        if status == "VM READ":
            self._s3270.enter()

        # read full output and format to return
        output = self._s3270.ascii()
        output = self._format_output(output, True)
        return output
    # login()

    def logoff(self, parameters=None):
        """
        Close the connection with the user depending on the parameter passed.

        Args:
            parameters (dict): dictionary with additional logoff parameters

        Returns:
            bool: True if connection was closed, False otherwise

        Raises:
            TimeoutError: if we have a timeout on connector
        """
        # logoff process
        self._s3270.clear()
        if parameters:
            if parameters.get("logoff"):
                self._s3270.string("#cp logoff")
        else:
            self._s3270.string("#cp disconnect")
        self._s3270.enter()

        # check if connection was closed
        if not self._is_connected():
            return True

        # connection was not closed
        return False
    # logoff()
