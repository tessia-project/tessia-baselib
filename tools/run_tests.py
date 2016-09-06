#!/usr/bin/env python3
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
Wrapper script to execute unit tests with unittest lib
"""

#
# IMPORTS
#
import os
import subprocess
import sys

#
# CONSTANTS AND DEFINITIONS
#
CMD_UNITTEST_DISCOVER = "python3 -m unittest discover -v {} -p '*.py'"
CMD_UNITTEST_MODULE = "python3 -m unittest -v {}"

#
# CODE
#
def main():
    """
    Process the command line arguments and create the appropriate unittest
    command

    Args:
        None

    Returns:
        None

    Raises:
        None
    """
    # determine repository's root dir
    my_dir = os.path.dirname(os.path.abspath(__file__))
    lib_dir = os.path.abspath('{}/..'.format(my_dir))

    # no arguments provided: execute all tests
    if len(sys.argv) < 2:
        cmd = CMD_UNITTEST_DISCOVER.format('tests/unit')
    # module path provided: use module's command version
    elif sys.argv[1].endswith('.py'):
        cmd = CMD_UNITTEST_MODULE.format(sys.argv[1])
    # package path provided: use discover option
    else:
        cmd = CMD_UNITTEST_DISCOVER.format(sys.argv[1])

    # switch to root dir to make sure paths are found
    cmd = 'cd {} && {}'.format(lib_dir, cmd)

    # show command line to user
    print(cmd)

    # execute and return exit code
    return subprocess.call(cmd, shell=True)
# main()

if __name__ == '__main__':
    sys.exit(main())
