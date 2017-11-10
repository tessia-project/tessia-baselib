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

'''
Module for exceptions used in zhmc package
'''
#
# IMPORTS
#


#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#


class ZHmcError(Exception):
    """
    Base class for exceptions raised by this module.
    """
    pass

class ZHmcRequestError(ZHmcError):
    """
    Raised when an API request ends in error or not as expected.
    """

    def __init__(self, status, reason=0, message=None, stack=None):
        """
        Constructor.

        Args:
            status (int): HTTP status code from the request
            reason (int): API reason code from the request
            message (str): API diagnostic message from the request
            stack (str): Internal HMC diagnostic info for Status 500 errors
        """
        super().__init__()
        self.args = status, reason, message
        self.status = status
        self.reason = reason
        self.message = message
        self.stack = stack
