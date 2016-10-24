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
Module for utility functions
"""
#
# IMPORTS
#
from time import sleep

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
def timer(cmd_channel, cmd, times, error_msg):
    """
    Auxiliary function for polling for a command until it is successfully
    executed. The number of trials and delay between each trial is defined by
    the times argument.

    Args:
    cmd_channel (object): An object that provides a method in the format
                          "run(self, cmd, timeout=120):". This method is used
                          to perform commands in a target connected by
                          channel.
    cmd (str): Command to be performed.
    times (list): interval to wait in each trial (i.e. [1, 2, 5])
    error_msg (str): error message to raise in case of failure

    Returns:
        None

    Raises:
        RuntimeError: In case there is no success executing the command
                      after waiting the consecutive wait times.
    """
    for n_times in times:
        sleep(n_times)
        ret, _ = cmd_channel.run(cmd)
        if ret == 0:
            break
    if ret != 0:
        raise RuntimeError(error_msg)
# timer()
