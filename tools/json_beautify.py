#!/usr/bin/env python3
# Copyright 2017 IBM Corp.
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
Simple script to parse a json file and indent it accordingly.
"""

#
# IMPORTS
#
import json
import sys

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
def main():
    """
    Entry point.
    """
    if len(sys.argv) < 2:
        print('Error: missing file path', file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]
    with open(file_path, 'r') as file_fd:
        content = file_fd.read().strip()
    if len(content) == 0:
        return 0
    result = json.dumps(
        json.loads(content), sort_keys=True, indent=4)
    with open(file_path, 'w') as file_fd:
        file_fd.write(result)

    return 0
# main()

if __name__ == '__main__':
    sys.exit(main())
