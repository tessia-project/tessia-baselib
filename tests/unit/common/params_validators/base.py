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
Module for unit tests of the BaseParamsValidator class.
"""

#
# IMPORTS
#
from tessia_baselib.common.params_validators.base import BaseParamsValidator
from unittest import mock

import unittest

#
# CONSTANTS AND DEFINITIONS
#
INEXISTENT_FILE = "randon_file_name"
INVALID_JSON = "{"
SOME_FILE = "some file"

#
# CODE
#

class TestBaseParamsValidator(unittest.TestCase):
    """
    Test the base class that is used to implement each params validator.
    """
    @mock.patch("tessia_baselib.common.params_validators.base.open", create=True)
    @mock.patch("tessia_baselib.common.params_validators.base.json", autospect=True)
    @mock.patch("tessia_baselib.common.params_validators."
                "base.BaseParamsValidator._check_schema", autospect=True)
    @mock.patch("tessia_baselib.common.params_validators.base.os", autospect=True)
    def test_constructor(self, mock_os, mock_check_schema,
                         mock_json, mock_open):
        """
        Test the constructor of the base class assuming all the arguments
        were properly used.

        Args:
            mock_os: Mock for the os module.
            mock_check_schema: Mock for the _check_schema method.
            mock_json: Mock for the json module.
            mock_open: Mock for the builtin open function.

        Returns:
            None

        Raises:
            None
        """
        mock_fp = mock.Mock()
        mock_open.return_value = mock_fp
        mock_os.path.abspath.return_value = SOME_FILE
        #Returns a empty dictionary
        mock_json.load.return_value = {}

        base = BaseParamsValidator(SOME_FILE)

        #Asserts that we are opening the file correctly.
        mock_open.assert_called_with(SOME_FILE, "r")
        #Asserts that the json was correctly loaded from the file.
        mock_json.load.assert_called_with(mock_fp)
        mock_os.path.abspath.assert_called_with(SOME_FILE)

        #Asserts that the id property of the dictionary was properly set.
        self.assertEqual(base.schema.get("id"), "file://" + SOME_FILE)
        #Asserts that the schema was checked
        self.assertEqual(mock_check_schema.call_count, 1)
    # test_constructor()

    def test_schema_file_not_found(self):
        """
        Test the case that the schema file is not found
        Args:
            None

        Returns:
            None

        Raises:
            None
        """
        self.assertRaises(FileNotFoundError,
                          BaseParamsValidator,
                          INEXISTENT_FILE)
    # test_schema_file_not_found()

    @mock.patch("tessia_baselib.common.params_validators.base.open", create=True)
    def test_schema_not_valid_json(self, mock_open):
        """
        Test the case that the json contained in the schema file is not a valid
        json.

        Args:
            mock_open: Mock for the builtin open function.

        Returns:
            None

        Raises:
            None
        """
        mock_fp = mock.Mock()
        #we change the return value of the read function in order to return
        #an invalid json.
        mock_fp.read.return_value = INVALID_JSON
        mock_open.return_value = mock_fp

        self.assertRaises(ValueError, BaseParamsValidator, "")
    # test_schema_not_valid_json()
#TestBaseParamsValidator
