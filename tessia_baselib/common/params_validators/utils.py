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
from tessia_baselib.common.params_validators.jsonschema import JsonschemaValidator
from tessia_baselib.config import CONF

import inspect
import os
#
# CONSTANTS AND DEFINITIONS
#
ARGUMENT_TO_VALIDATE = "parameters"
SCHEMAS_BASE_DIR = os.path.dirname(os.path.realpath(__file__)) + "/schemas"
VALID_ACTIONS = ("start", "stop", "hotplug", "__init__", "reboot")
VALIDATOR_LIBS = {
    "jsonschema": JsonschemaValidator
}

#
# CODE
#

def create_params_validator(json_schema_file, validator=None):
    """
    This functions is a factory for json schema validators.
    Args:
        json_schema_file: Path to the file containing the json schema.
        validator: Name (string) of the validator that will be instantiated.
                   If no name is provided, it will use the default validator
                   defined in the configuration file.

    Returns:
        An instance of the chosen parameters validator.

    Raises:
        ValueError: It the default validator is not defined in the
                    configuration file or it is not a supported validator.
    """
    if validator is None:
        try:
            validator_lib = CONF.get_config()["default_schema_validator"]
        # config file not available or missing option: use jsonschema
        except (KeyError, IOError):
            validator_lib = 'jsonschema'
    else:
        validator_lib = validator

    if validator_lib not in VALIDATOR_LIBS.keys():
        raise ValueError(
            "{} is not a valid validator. Use one of {}".format(
                validator_lib, ', '.join(VALIDATOR_LIBS.keys()))
        )

    return VALIDATOR_LIBS[validator_lib](json_schema_file)
# create_params_validator()

def validate_params(func):
    """
    A function decorator that is used to validate the "parameters" argument
    of a function.

    Usage:
        @validate_params
        def start(arg1, arg2, parameters):
            ...

    Raises:
        NameError if the function name is not valid, and if the "parameters"
        argument is not found.
    """
    func_name = func.__name__

    #Only valid actions can be decorated with @validate_params
    if func_name not in VALID_ACTIONS:
        raise NameError("validate_params should only decorate functions"
                        "in {}".format(VALID_ACTIONS))

    func_specs = inspect.getfullargspec(func)
    # get the correct function argument
    try:
        parameters_index = func_specs.args.index(ARGUMENT_TO_VALIDATE)
        #the parameter to validate must be present in the function parameters
    except ValueError as ex:
        raise NameError("Decorated function does not have correct argument"
                        "to validate: {}".format(ARGUMENT_TO_VALIDATE))

    #gather information about the module in order to choose the proper
    #json schema
    func_file = inspect.getfile(func)
    func_dir_name = os.path.dirname(func_file).split("/")[-1]

    #all json schemas must be placed inside the
    #tessia_baselib/common/validators/jsonschemas directory according to the
    #name of the module
    schema_file = SCHEMAS_BASE_DIR + "/" + func_dir_name \
                  + "/actions/" + func_name + ".json"

    validator = create_params_validator(schema_file)

    def validate(*params):
        """
        Inner function of the decorator
        """
        validator.validate(params[parameters_index])

        return func(*params)
    # validate()

    return validate
# validate_params()
