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

#pylint:skip-file
"""
Module for unit tests of the JsonschemaValidator class.
"""

#
# IMPORTS
#
from tessia.baselib.common.params_validators.jsonschema import JsonschemaValidator
from unittest import mock

import unittest
#
# CONSTANTS AND DEFINITIONS
#

INVALID_JSONSCHEMA = {"type": "unknown"}
NUMBER_ONLY_SCHEMA = {"type": "number"}
VALID_SCHEMA = {}
VALID_DATA = 1

#
# CODE
#
class TestJsonschemaValidator(unittest.TestCase):
    """
    Unit test for the JsonschemaValidator class
    """
    @mock.patch('tessia.baselib.common.params_validators.base.json', autospec=True)
    @mock.patch('builtins.open', autospec=True)
    def test_schema_not_valid(self, mock_open, mock_json):
        """
        Test the case that an invalid json schema is provided.
        Args:
            mock_open Mock for the builtin open function
            mock_json Mock for the json module

        Returns:
            None

        Raises:
            None
        """
        mock_json.load.return_value = INVALID_JSONSCHEMA
        self.assertRaises(ValueError, JsonschemaValidator, "any_place")
    # test_schema_not_valid()

    @mock.patch('tessia.baselib.common.params_validators.base.json', autospec=True)
    @mock.patch('builtins.open', autospec=True)
    def test_validation_error(self, mock_open, mock_json):
        """
        Test the case that the json data to be validated does not conform
        to the json schema.
        Args:
            mock_open Mock of the builtin open function.
            mock_json Mock of the json module.
        Returns:
            None

        Raises:
            None
        """
        mock_json.load.return_value = NUMBER_ONLY_SCHEMA
        validator = JsonschemaValidator("any_place")
        self.assertRaises(ValueError, validator.validate, "string")
    # test_validation_error()

    @mock.patch('tessia.baselib.common.params_validators.jsonschema.jsonschema')
    @mock.patch('tessia.baselib.common.params_validators.jsonschema.FormatChecker')
    @mock.patch('tessia.baselib.common.params_validators.base.json', autospec=True)
    @mock.patch('builtins.open', autospec=True)
    def test_validate(self, mock_open, mock_json, mock_fmt_checker,
                      mock_jsonschema):
        """
        Test the case that a json data is successfully validated
        against the json schema.

        Args:
            mock_open: Mock of the builtin open function.
            mock_json: Mock of the json module.
            mock_fmt_checker: Mock of the FormatChecker class.
            mock_jsonschema: Mock of the jsonschema module.

        Returns:
            None

        Raises:
            None
        """
        #We do not assert the open function here since it was already tested
        #in the base class.
        mock_json.load.return_value = VALID_SCHEMA

        validator = JsonschemaValidator("any_place")

        #Assert that the json schema was properly checked.
        check_schema_method = mock_jsonschema.Draft4Validator.check_schema
        check_schema_method.assert_called_once_with(VALID_SCHEMA)

        validator.validate(VALID_DATA)

        validate_function = mock_jsonschema.validate
        draft4_class = mock_jsonschema.Draft4Validator
        #Assert tha the data was validated against the json schema.
        validate_function.assert_called_once_with(
            VALID_DATA, VALID_SCHEMA,
            cls=draft4_class,
            format_checker=mock_fmt_checker.return_value)
    # test_validate()
# TestJsonschemaValidator
