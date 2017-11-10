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
Module for JsonschemaValidator class.
"""
#
# IMPORTS
#
from .base import BaseParamsValidator
# the FormatChecker is used to validate URIs
from jsonschema import FormatChecker
import jsonschema

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
class JsonschemaValidator(BaseParamsValidator):
    """
    This class implements a validator that uses the jsconschema
    library to validate json schemas.
    Jsonschema https://github.com/Julian/jsonschema
    """
    def _check_schema(self):
        """
        Checks if the loaded json schema is valid. This method is dependent of
        the chosen library that implement json schema validation.
        Args:
            None

        Raises:
            ValueError: if the json schema loaded is not valid.
        """
        try:
            jsonschema.Draft4Validator.check_schema(self.schema)
        except jsonschema.SchemaError as exc:
            raise ValueError("Invalid schema") from exc
    # _check_schema()

    def validate(self, parameters):
        """
        Validate parameters against the loaded json schema. This method is
        dependent of the chosen library that implement json schema validation.
        Args:
            parameters (dict): A dictionary that will be validated.

        Raises:
            ValueError: If parameters fails to validate against the loaded json
                        schema.
        """
        try:
            jsonschema.validate(parameters, self.schema,
                                cls=jsonschema.Draft4Validator,
                                format_checker=FormatChecker())
        except jsonschema.ValidationError as exc:
            raise ValueError("Invalid parameter for jsonschema") from exc
    # validate()
# JsonschemaValidator
