# Copyright 2016, 2017, 2018 IBM Corp.
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
from tessia.baselib.common.logger import get_logger
from tessia.baselib.common.s3270.exceptions import S3270StatusError
from tessia.baselib.common.s3270.exceptions import ZvmMessageError
from tessia.baselib.common.s3270.s3270 import S3270
from time import time
from time import sleep

import re

#
# CONSTANTS AND DEFINITIONS
#
# zVM messages and codes
ERROR_REGEX = r'(HCP(?:[a-zA-Z]{0,8})\d{1,4}[E]{1})( .*)?'
ZVM_CODES = {
    "RPIMGR042I": "PASSWORD EXPIRED",
    "RPIMGR046T": "User ID access has been revoked.",
    "HCPCFC015E": "Command not valid before LOGON",
    "HCPLGA050E": "LOGON unsuccessful--incorrect userid and/or password",
    "HCPLGA054E": "Already logged on",
    "HCPUSO361E": "LOGOFF/FORCE pending for user",
    "HCPLGA361E": "LOGOFF/FORCE pending for user",
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

        Raises:
            None
        """
        # intialize logger object
        self._logger = get_logger(__name__)

        # variable to hold s3270 object, initialized when connection is
        # established
        self._s3270 = None
    # __init__()

    @staticmethod
    def _check_output(text):
        """
        Look for zVM error codes into the text and return it when found.

        Args:
            text (str): text to be checked

        Returns:
            tuple: error_code, message corresponding to the code
            None: No error code found
        """
        # check line by line of text
        for line in text.splitlines():
            # check if error message is in the beginning of the line
            if line[1:11] in ZVM_CODES:
                # return error message
                return line[1:11], ZVM_CODES[line[1:11]]

            # check for general errors
            re_match = re.search(ERROR_REGEX, line)
            if re_match:
                error_code = re_match.group(1)
                error_msg = re_match.group(2)
                if error_msg is None:
                    error_msg = ''
                return error_code, error_msg.strip()

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
        if output:
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
    def _cleanup_status_line(output):
        """
        Cleanup last line and status line from output

        Args:
            output (str): output to be cleaned

        Returns:
            str: output without status line

        Raises:
            None
        """
        # remove last bank line
        output = output.rstrip('\n')
        # remove MORE... or HOLDING line
        output = output[:output.rfind('\n')+1]

        return output
    # _cleanup_status_line()

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

        lines = text.strip().splitlines()
        # no text to format: nothing to do
        if not lines:
            return output

        # ignore last 2 lines (flags and status)
        if lines[-1].startswith('ok'):
            lines.pop()
        if (lines[-1].startswith('U F U') or
                lines[-1].startswith('U U U') or
                lines[-1].startswith('L U U')):
            lines.pop()

        # check line by line of text
        for line in lines:
            # remove 'data:' from the beginning
            if line.startswith('data:'):
                line = line[5:]
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
        Check if current object is connected to a host by querying the host
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
        # no s3270 process: no open connection
        if not self._s3270:
            return False

        # query host
        output = self._s3270.query()

        # remove unnecessary data
        output = self._format_output(output, strip=True)

        # check if object has a connection
        if self._s3270.host_name and self._s3270.host_name in output:
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
        if status in cp_status:
            return True

        return False
    # _is_output_full()

    def _parse_output(self, wait_for=None, timeout=60):
        """
        Parse the output looking for 'wait_for'.

        Args:
            wait_for (list): [regex_str1, regex_str2]
            timeout (int): how many seconds to wait for action to complete

        Returns:
            tuple: (str1, SRE_Match)
                str: full output until any of 'wait_for' matches or
                     timeout occurred
                SRE_Match: regex matched object
        """
        # matched regex
        matched_obj = None

        output = ''
        if wait_for:
            # define the timeout limit
            timeout = time() + timeout

            buf_output = None
            while time() < timeout:
                # read the current information on terminal and remove
                # unnecessary data
                buf_output = self._format_output(
                    self._s3270.ascii(), strip=True)

                # try to match collected output with any of the regexes
                # specified
                for match_re in wait_for:
                    matched_obj = re.search(match_re, buf_output)
                    # regex matched: stop processing
                    if matched_obj:
                        break

                # terminal is full: clear it
                if self._is_output_full(buf_output):
                    # append current information to the output
                    output += self._cleanup_status_line(buf_output)
                    self._s3270.clear()
                    # clear buffer so that it won't be appended twice to the
                    # collected output when we leave the loop
                    buf_output = None
                # machine in halted state: set again to running so that
                # pending output can be consumed
                elif self._check_status(buf_output) == 'VM READ':
                    output += self._cleanup_status_line(buf_output)
                    self._s3270.enter()
                    # clear buffer so that it won't be appended twice to the
                    # collected output when we leave the loop
                    buf_output = None

                # expected pattern matched: stop waiting
                if matched_obj:
                    break

                # sleep for a while to avoid cpu consumption
                sleep(0.2)

            # leftover output available: append it to collected output
            if buf_output:
                output += self._cleanup_status_line(buf_output)

        else:
            # fetch all available output
            output_full = True
            while output_full:
                buf_output = self._format_output(
                    self._s3270.ascii(), strip=True)

                # machine in halted state: set again to running so that
                # pending output can be consumed
                if self._check_status(buf_output) == 'VM READ':
                    output += self._cleanup_status_line(buf_output)
                    self._s3270.enter()
                    continue

                # in case output is not full we will leave the loop as all
                # available output was already collected
                output_full = self._is_output_full(buf_output)
                output += self._cleanup_status_line(buf_output)
                # clear screen to consume more output
                self._s3270.clear()

        return (output, matched_obj)
    # _parse_output()

    def connect(self, host_name, timeout=60):
        """
        Connects to the hostname provided.

        Args:
            host_name (str): target hostname
            timeout (int): how many seconds to wait for connection

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

        # process object does not exist yet: create it
        if not self._s3270:
            self._s3270 = S3270()

        # create a s3270 connection to the host using our s3270 module
        self._s3270.connect(host_name, timeout)
    # connect()

    def disconnect(self):
        """
        Disconnect from user.
        """
        if not self._is_connected():
            raise RuntimeError('Not connected or connection to host was lost.')

        # disconnect and quit
        self._s3270.clear()
        self._s3270.string("#cp disconnect")
        self._s3270.enter()
        # cleanup process and object
        self._s3270.quit()
        self._s3270 = None
    # disconnect()

    @property
    def host_name(self):
        """
        Return the hostname of the current connection

        Returns:
            str: hostname currently connected
        """
        if self._s3270:
            return self._s3270.host_name
        return None
    # host_name

    def send_cmd(self, cmd, use_cp=False, wait_for=None, timeout=60):
        """
        Issue a command on zVM.

        Args:
            cmd (str): command to be executed
            use_cp (bool): whether the command should be executed on CP
            wait_for (list): [regex_str1, regex_str2] or regex_str1
            timeout (int): how many seconds to wait for command to execute

        Returns:
            tuple: (str1, SRE_Match)
                str: full output until any of 'wait_for' matches or
                     timeout occurred
                SRE_Match: regex match object

        Raises:
            RuntimeError: if connection to the host was lost
        """
        if not self._is_connected():
            raise RuntimeError('Not connected or connection to host was lost.')

        if isinstance(wait_for, str):
            wait_for = [wait_for]

        # make sure we have a clear screen for output
        self._s3270.clear()
        # put command on input line
        if use_cp:
            self._s3270.string("#cp "+cmd)
        else:
            self._s3270.string(cmd)
        # issue the command
        self._s3270.enter()

        # return output and matched regex of command issued
        return self._parse_output(wait_for, timeout)
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
            TimeoutError: a timeout on connector or force pending never
                          releases
            S3270StatusError: if protocol error occurred
            ZvmMessageError: if we have a zVM message code
        """
        login_cmd = 'l ' + user
        # setup aditional login parameters
        if parameters:
            # check if we will do a logon by
            if parameters.get('byuser'):
                login_cmd += ' by ' + parameters.get('byuser')
            # check if we will do a logon here
            if parameters.get('here'):
                login_cmd += ' here'
            # noipl specified: do not ipl user directory entry
            if parameters.get('noipl'):
                login_cmd += ' noipl'

        time_limit = time() + timeout

        # create an s3270 connection to the host
        self.connect(host_name, timeout)
        self._s3270.clear()

        cur_cmd = login_cmd
        while True:
            self._s3270.string(cur_cmd)
            self._s3270.enter()
            output = self._s3270.ascii()
            error_msg = self._check_output(self._format_output(output))
            # no errors: process next command
            if not error_msg:
                # no more commands: login process finished
                if cur_cmd == password:
                    break
                # move to next step, enter password
                cur_cmd = password
                continue

            # in case a pending logoff/force occurs try to wait until it's
            # finished
            if error_msg[0] in ['HCPUSO361E', 'HCPLGA361E']:
                if time() > time_limit:
                    raise TimeoutError('{} {}'.format(*error_msg))
                # remove error message from output before trying again
                self._s3270.clear()
                # start over, enter user
                cur_cmd = login_cmd
                # wait a while and try again
                sleep(0.2)
                continue

            # another type of error occurred: cannot continue
            raise ZvmMessageError('{} {}'.format(*error_msg))

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
        output = self._cleanup_status_line(output)
        self._s3270.clear()

        return output
    # login()

    def logoff(self):
        """
        Logoff from user.
        """
        if not self._is_connected():
            raise RuntimeError('Not connected or connection to host was lost.')

        # logoff and quit
        self._s3270.clear()
        self._s3270.string("#cp logoff")
        self._s3270.enter()
        # cleanup process and object
        self._s3270.quit()
        self._s3270 = None
    # logoff()

    def transfer(self, *args, **kwargs):
        """
        Send/receive a file to/from the host via the transfer command. See
        S3270.transfer() for details.
        """
        if not self._is_connected():
            raise RuntimeError('Not connected or connection to host was lost.')
        try:
            output = self._s3270.transfer(*args, **kwargs)
        except S3270StatusError as exc:
            # format the output consumed until the exception happened
            output = self._format_output(exc.output, True).strip()
            raise RuntimeError(
                'Transfer failed, output: {}'.format(output))

        return self._format_output(output, True)
    # transfer()
# Terminal
