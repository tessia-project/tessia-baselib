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
S3270 package exceptions classes
"""
#
# IMPORTS
#

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
# this module defines all the exceptions used by s3270 package
class S3270StatusError(Exception):
    """
    Exception used by s3270 when a status is different from 'ok'.
    """
    def __init__(self, msg, output=None):
        """
        Store the output of the failed command.

        Args:
            msg (str): exception's error message
            output (str): output collected when error occurred
        """
        super().__init__(msg)
        self.output = output
    # __init__()
# S3270StatusError

class ZvmMessageError(Exception):
    """
    Exception used by terminal when a code from a system message is found.
    """
# ZvmMessageError
