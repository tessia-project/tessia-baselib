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

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

class GuestSessionBase(object):
    """
    This is the abstract class which defines the interface to be implemented
    by each guest driver when returning a session object from openSession
    method.
    """

    def __init__(self):
        """
        This constructor should be overriden by concrete classes
        """
        raise NotImplementedError()
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
        raise NotImplementedError()
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
        raise NotImplementedError()
    # run()

# GuestSessionBase
