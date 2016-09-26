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
Wrapper script to execute coverage3 on unit tests
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
CMD_COVERAGE = "python3 -m coverage run -a --source={} -m unittest -v {}"
CMD_ERASE = "coverage erase"
#
# CODE
#
def main():
    """
    Process the command line arguments and create the appropriate coverage3
    command

    Args:
        Optional    Relative path to test

    Returns:
        None

    Raises:
        Exception   If the operation fails
    """

    # erase previously collected coverage data
    subprocess.call(CMD_ERASE, shell=True)

    my_dir = os.path.dirname(os.path.abspath(__file__))
    lib_dir = os.path.abspath('{}/..'.format(my_dir))

    # return value
    ret = 0

    # module path provided
    if len(sys.argv) > 1:
        cmd = CMD_COVERAGE.format(
            sys.argv[1].replace("tests/unit", "tessia_baselib"),
            sys.argv[1]
        )
        ret += subprocess.call(cmd, shell=True)
    else:
        # search in the directory /tests/unit for all tests
        for root, dirs, files in os.walk(lib_dir + "/tests/unit"):
            for name in files:
                # skip __init__.py files
                if name.endswith(".py") and name != "__init__.py":
                    test_abs_path = os.path.join(root, name)

                    test_rel_path = os.path.relpath(test_abs_path, lib_dir)
                    source = test_abs_path.replace(
                        "/tests/unit", "/tessia_baselib"
                    )

                    cmd = CMD_COVERAGE.format(source, test_rel_path)

                    # show command line to user
                    print(cmd)

                    cmd = 'cd {} && {}'.format(lib_dir, cmd)
                    ret += subprocess.call(cmd, shell=True)

    # display report
    subprocess.call("python3 -m coverage report -m", shell=True)

    if ret != 0:
        raise Exception(
            "A tess contain an error or the coverage command failed to run."
        )
# main()

if __name__ == '__main__':
    sys.exit(main())
