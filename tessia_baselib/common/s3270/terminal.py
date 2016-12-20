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

    @staticmethod
    def _format_output(text, full=False):
        """
        Format the text to remove s3270 tags, s3270 flags,
        status line and blank lines.

        Args:
            text (str): text to be formated
            full (bool): remove blank lines

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
            # remove blank lines when set to full parse
            if full:
                if line.strip():
                    output += line+'\n'
            else:
                output += line+'\n'
        return output
    # _format_output()

    def _is_connected(self):
        """
        check if current object is connected to a host by quering the host
        attribute. When there is a connection opened, query will return the
        hostname. When there is not a connection opened, query will return
        an empty string.

        Args:
            None

        Returns:
            bool: if connected to a host, False otherwise

        Raises:
            None
        """
        # If hostname was not set yet, a connection was not opened.
        if not self.host_name:
            return False

        # query host
        output = self._s3270.query()

        # remove unnecessary data
        output = self._format_output(output, full=True)

        # check if object has a connection
        if self.host_name in output:
            return True
        return False
    #_is_connected()

    def _parse_output(self, text, wait_for=''):
        """
        Parse the text to implement terminal scrolling.

        Args:
            text (str): text to be parsed
            wait_for (str): string to stop parsing

        Returns:
            None

        Raises:
            NotImplementedError: to be implemented
        """
        raise NotImplementedError()
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
            str: output of run command

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

        output = self._format_output(output, True)
        return output
    # login()
