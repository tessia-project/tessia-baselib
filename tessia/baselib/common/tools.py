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
Misc utilities to be used by other modules
"""

#
# IMPORTS
#
from importlib import util

import glob
import os

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
def import_modules(modules_path, skip_list=None):
    """
    Dynamically imports python modules found in the provided directory and
    returns a list of the module objects found.

    Args:
        modules_path (str): filesystem path containing modules to import
        skip_list (list): module names to skip, usually the caller module

    Returns:
        list: module objects imported

    Raises:
        SyntaxError: if some module cannot be imported
    """
    # skip list not defined: create an empty one
    if skip_list is None:
        skip_list = []
    # make sure __init__ is not loaded
    skip_list.append('__init__')

    # lists python files in the current directory
    dir_entries = glob.glob(os.path.join(modules_path, '*.py'))

    # import each module and add its object to the final list

    # convert the list from filenames to module names and remove those in
    # skip list
    loaded_list = []
    for module_file in dir_entries:
        # remove the leading dir and file extension from the module name
        module_name = os.path.basename(module_file)[:-3]

        # module in skip list: do not load
        if module_name in skip_list:
            continue

        # we might hit a SyntaxError here
        spec = util.spec_from_file_location(module_name, module_file)
        module = util.module_from_spec(spec)
        spec.loader.exec_module(module)
        loaded_list.append(module)

    return loaded_list
# import_modules()
