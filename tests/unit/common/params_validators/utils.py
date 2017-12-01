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
Module for unit tests of the utility functions of the util module.
"""

#
# IMPORTS
from tessia.baselib.common.params_validators import utils
from unittest import mock

import unittest

#
# CONSTANTS AND DEFINITIONS
#
VALIDATOR_NOT_IN_LIBS = "any validator"

#
# CODE
#

class TestUtils(unittest.TestCase):
    """
    Unit tests for the utility functions of parameters validation.
    """
    def setUp(self):
        """
        Prepare the necessary mocks at the beginning of each testcase.
        """
        patcher = mock.patch.object(utils, "inspect", autospec=True)
        self._mock_inspect = patcher.start()
        self.addCleanup(patcher.stop)
    # setUp()

    def test_func_name_is_not_valid(self):
        """
        Test the case that the name of the function being decorated by
        validate_params is not valid.
        """
        mock_func = mock.Mock()

        mock_func.__name__ = "not_valid_function_name"

        self.assertRaisesRegex(NameError, "should only decorate",
                               utils.validate_params, mock_func)
    # test_func_name_is_not_valid()

    def test_func_argument_not_valid(self):
        """
        Test the case that the argument to be validated is not present
        in the arguments of the function being decorated by
        validate_params.
        """
        mock_func = mock.Mock()
        #We use a valid function name here
        mock_func.__name__ = "start"
        func_specs_mock = mock.Mock()
        self._mock_inspect.getfullargspec.return_value = func_specs_mock
        func_specs_mock.args.index.side_effect = ValueError("foo")

        self.assertRaisesRegex(NameError, "Decorated function does",
                               utils.validate_params, mock_func)
    # test_func_argument_not_valid()

    @mock.patch("tessia.baselib.common.params_validators.utils.os",
                autospec=True)
    @mock.patch("tessia.baselib.common.params_validators"
                ".utils.JsonschemaValidator", autospec=True)
    @mock.patch("tessia.baselib.common.params_validators"
                ".utils.SCHEMAS_BASE_DIR", new="BASE_DIR")
    def test_validate_params(self, mock_json_validator, mock_os):
        """
        Test that the decorator was properly used.

        Args:
            mock_json_validator (Mock): Mock of the JsonschemaValidator class
            mock_os (Mock): Mock of the os module
        """
        #Mock function that will be decorated
        func_name = "start"
        func = mock.Mock()
        func.__name__ = func_name

        func_signature = self._mock_inspect.signature.return_value
        # the parameters will be in the function argument array in the index 0
        func_signature.parameters.keys.return_value.__iter__.return_value = (
            ["parameters"])

        #Create a fake dir name for the function beeing decorated
        mock_os.path.dirname.return_value = "/dir1/dir2"

        #This is the fake full path for the schema
        schema_file = "BASE_DIR/dir2/actions/start.json"

        #call the software under test
        decorated_func = utils.validate_params(func)
        decorated_func(1, 2, 3)

        #Assert that the schema file full path was created correctly
        mock_json_validator.assert_called_with(schema_file)

        # Assert that the validator chose the correct parameter based on the
        # index returned by func_params.index
        mock_json_validator.return_value.validate.assert_called_with(1)

        #Assert that the function was called with correct arguments
        func.assert_called_with(1, 2, 3)
    # test_validate_params()
# TestUtils
