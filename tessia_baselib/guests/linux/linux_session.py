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
from tessia_baselib.common.ssh.exceptions import SshShellError
from tessia_baselib.guests.base_session import GuestSessionBase

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

class GuestSessionLinux(GuestSessionBase):
    """
    Linux implementation of the session object returned when openSession is
    called from a Guest object.
    """

    def __init__(self, sshShell):
        """
        Store the ssh shell object

        Args:
            None

        Returns:
            None

        Raises:
            None
        """
        self._sshShell = sshShell
    # __init__()

    def close(self):
        """
        Close the session, no more communication is possible.

        Args:
            None

        Returns:
            None

        Raises:
            None
        """
        self._sshShell.close()
        self._sshShell = None
    # close()

    def run(self, cmd, timeout=120):
        """
        Execute a command and wait timeout seconds for the completion.

        Args:
            cmd: command to execute
            timeout: seconds to wait for response

        Returns:
            tuple (integer_exit_code, string_output)

        Raises:
            RuntimeError: if any unexpected problem occurs
            TimeoutError: if timeout is reached and execution did not complete
        """
        # since the ssh shell interface is the same we can just call it
        # directly
        try:
            ret, output = self._sshShell.run(cmd, timeout)
        # catch specific ssh exception and re-raise with appropriate type to
        # keep the interface consistent
        except SshShellError as exc:
            raise RuntimeError(str(exc))

        return ret, output
    # run()

# GuestSessionLinux
