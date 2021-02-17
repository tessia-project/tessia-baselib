#!/usr/bin/env python3
# Copyright 2021 IBM Corp.
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
Wrapper script to execute unit tests
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
CMD_RUN_PYTEST = "python3 -m pytest {}"

#
# CODE
#
def main():
    """
    Execute pytest command

    Args:
        None

    Returns:
        int: exit code from pytest shell command

    Raises:
        None
    """
    # determine repository's root dir
    my_dir = os.path.dirname(os.path.abspath(__file__))
    lib_dir = os.path.abspath('{}/..'.format(my_dir))
    os.chdir(lib_dir)

    cmds = []

    # execute all tests
    cmds.append(CMD_RUN_PYTEST.format('tests_pytest'))

    # show command line to user
    cmd = ' && '.join(cmds)
    print(cmd)

    # execute and return exit code
    return subprocess.call(cmd, shell=True)
# main()

if __name__ == '__main__':
    sys.exit(main())
