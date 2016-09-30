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
Provides logging utilites for other modules
"""

#
# IMPORTS
#
import logging

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
def get_logger(logger_name, propagate=True):
    """
    This function provides a simple wrapper to add a null handler to the logger
    requested so that we make sure not to dump stuff to terminal as defined by
    default configuration in case the library user do not want to use logging
    (or didn't care about configuring it).

    Args:
        logger_name (str): the logger instance name (usually the module name
                           with __name__)
        propagate (bool): whether to propagate the messages up to ancestor
                          loggers

    Returns:
        logging.Logger: Logger instance

    Raises:
        None
    """
    # if logger instance does not exist it will be created upon call
    logger = logging.getLogger(logger_name)
    logger.propagate = propagate

    # add the null handler to make sure nothing is written in case user didn't
    # configure logging
    logger.addHandler(logging.NullHandler())

    return logger
# get_logger()
