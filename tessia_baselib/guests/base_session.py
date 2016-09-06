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
Interface for sessions objects established on guests
"""

#
# IMPORTS
#
import abc

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

class GuestSessionBase(metaclass=abc.ABCMeta):
    """
    This is the abstract class which defines the interface to be implemented
    by each guest driver when returning a session object from open_session
    method.
    """

    @abc.abstractmethod
    def close(self):
        """
        Close the session, no more communication is possible.

        Args:
            None

        Returns:
            None

        Raises:
            NotImplementedError: this method should be implemented by children
        """
        raise NotImplementedError()
    # close()

    @abc.abstractmethod
    def run(self, cmd, timeout=120):
        """
        Execute a command and wait timeout seconds for the completion.
        It should raise the following exceptions:
            RuntimeError: if any unexpected problem occurs
            TimeoutError: if timeout is reached and execution did not complete

        Args:
            cmd (str): command to execute
            timeout (int): seconds to wait for response

        Returns:
            tuple (integer_exit_code, string_output)

        Raises:
            NotImplementedError: this method should be implemented by children
        """
        raise NotImplementedError()
    # run()

# GuestSessionBase
