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

#
# IMPORTS
#
from tessia_baselib.common.tools import importModules
from importlib.machinery import SourceFileLoader
from tempfile import TemporaryDirectory
from unittest import TestCase

import os

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

class TestImportModules(TestCase):
    """
    Unit test for the importModules function.
    To best exercise the function let the function really import modules
    instead of creating mocks that will fake some answers (since the involved
    libraries won't be tested anywhere else).
    """
    def _createModule(self, file_path, file_content):
        """
        Helper function to create a dummy module with content provided.

        Args:
            content: module file content

        Returns:
            module object

        Raises:
            None
        """
        # create dummy module import os
        modFile = open(file_path, 'w')
        modFile.write(file_content)
        modFile.close()

        moduleObj = SourceFileLoader(
            os.path.basename(file_path[:-3]), file_path).load_module()

        return moduleObj
    # _createModule()

    def setUp(self):
        """
        Create a temporary directory and some simple modules.

        Args:
            None

        Returns:
            None

        Raises:
            None
        """
        # create temp directory
        self.tempDir = TemporaryDirectory(prefix='unit_test-')

        # create dummy module list_dir
        dummy_content = "import os\n"
        dummy_content += "def list_dir(user_dir):\n"
        dummy_content += "    print(os.listdir(user_dir))\n"
        # create module object
        module_path = os.path.join(self.tempDir.name, 'list_dir.py')
        self.modListdir = self._createModule(module_path, dummy_content)

        # create dummy module match_re
        dummy_content = "import re\n"
        dummy_content += "def match_re(regex, content):\n"
        dummy_content += "    return re.search(regex,content)\n"
        # create module object
        module_path = os.path.join(self.tempDir.name, 'match_re.py')
        self.modMatchre = self._createModule(module_path, dummy_content)

        # create __init__ file
        module_path = os.path.join(self.tempDir.name, '__init__.py')
        self.modInit = self._createModule(module_path, '')

        # create two non .py files
        open(os.path.join(self.tempDir.name, 'dummy.txt'), 'w').close()
        open(os.path.join(self.tempDir.name, 'dummy'), 'w').close()
    # setUp()

    def tearDown(self):
        """
        Cleanup the fixture (test environment) by removing the temporary
        modules and directory.

        Args:
            None

        Returns:
            None

        Raises:
            None
        """
        self.tempDir.cleanup()
    # tearDown()

    def test_normal_flow_empty_skip(self):
        """
        Exercise the module importing with an empty skip list.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the result from function call is not correct
        """
        # let the function do its work
        loaded_list = importModules(self.tempDir.name)

        # assemble the list we expect it to have created
        expected_list = [
            self.modListdir,
            self.modMatchre
        ]

        # here we exercise the module importing and the excluding of the
        # __init__ and non .py files from the directory
        self.assertEqual(set(loaded_list), set(expected_list))

    # test_normal_flow_empty_skip()

    def test_normal_flow_some_skip(self):
        """
        Exercise the module importing with a populated skip list.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the result from function call is not correct
        """
        # let the function do its work
        loaded_list = importModules(self.tempDir.name, skip_list=['list_dir'])

        # assemble the list we expect it to have created
        expected_list = [self.modMatchre]

        # here we exercise the module importing and the excluding of the
        # __init__ (but not in skip list) and non .py files from the directory
        self.assertEqual(set(loaded_list), set(expected_list))
    # test_normal_flow_some_skip()

    def test_normal_flow_init_skip(self):
        """
        Exercise the module importing with __init__ in the skip list. This test
        is relevant because __init__ is special and already skipped by default
        so here we make sure the function does not mix up things.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the result from function call is not correct
        """
        # let the function do its work
        loaded_list = importModules(self.tempDir.name, skip_list=['__init__'])

        # assemble the list we expect it to have created
        expected_list = [
            self.modListdir,
            self.modMatchre
        ]

        # here we exercise the module importing and the excluding of the
        # __init__ in the skip list and non .py files from the directory
        self.assertEqual(set(loaded_list), set(expected_list))
    # test_normal_flow_init_skip()

    def test_invalid_module(self):
        """
        Exercise the module importing with an empty skip list.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if the result from function call is not correct
        """
        # create an invalid module
        invalidFile = open(os.path.join(self.tempDir.name, 'invalid.py'), 'w')
        invalidFile.write('invalid content')
        invalidFile.close()

        # exercise the function raising exception due to an invalid module
        # found
        self.assertRaises(SyntaxError, importModules, self.tempDir.name)

    # test_invalid_module()

# TestImportModules
