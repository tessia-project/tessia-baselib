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
from tessia.baselib.common.params_validators.jsonschema import \
    JsonschemaValidator

import inspect
import os
#
# CONSTANTS AND DEFINITIONS
#
ARGUMENT_TO_VALIDATE = "parameters"
SCHEMAS_BASE_DIR = os.path.dirname(os.path.realpath(__file__)) + "/schemas"
VALID_ACTIONS = ("start", "stop", "hotplug", "__init__", "reboot")

#
# CODE
#
def validate_params(func):
    """
    A function decorator that is used to validate the "parameters" argument
    of a function.

    Usage:
        @validate_params
        def start(arg1, arg2, parameters):
            ...
    Returns:
        func: Decorated function.

    Raises:
        NameError: if the function name is not valid, and if the "parameters"
        argument is not found.
    """
    func_name = func.__name__

    # Only valid actions can be decorated with @validate_params
    if func_name not in VALID_ACTIONS:
        raise NameError("validate_params should only decorate functions"
                        "in {}".format(VALID_ACTIONS))
    func_signature = inspect.signature(func)
    func_params = list(func_signature.parameters.keys())
    # get the correct function argument
    try:
        parameters_index = func_params.index(ARGUMENT_TO_VALIDATE)
    # the parameter to validate must be present in the function parameters
    except ValueError:
        raise NameError("Decorated function does not have correct argument"
                        "to validate: {}".format(ARGUMENT_TO_VALIDATE))

    # gather information about the module in order to choose the proper
    # json schema
    func_file = inspect.getfile(func)
    func_dir_name = os.path.dirname(func_file).split("/")[-1]

    # all json schemas must be placed inside the
    # tessia/baselib/common/validators/jsonschemas directory according to the
    # name of the module
    schema_file = SCHEMAS_BASE_DIR + "/" + func_dir_name \
                  + "/actions/" + func_name + ".json"

    validator = JsonschemaValidator(schema_file)

    def validate(*params):
        """
        Inner function of the decorator
        """
        if (len(params)-1) < parameters_index:
            raise ValueError("Method call has missing argument '{}'".format(
                ARGUMENT_TO_VALIDATE))
        validator.validate(params[parameters_index])

        return func(*params)
    # validate()

    return validate
# validate_params()
