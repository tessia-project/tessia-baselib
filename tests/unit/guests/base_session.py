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
Unit test for module guests.base_session
"""

#
# IMPORTS
#
from tessia.baselib.guests.base_session import GuestSessionBase
from unittest import TestCase

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

class TestGuestSessionBase(TestCase):
    """
    Unit test for the GuestSessionBase class
    """
    def setUp(self):
        """
        Prepare necessary objects before executing each testcase

        Args:
            None

        Raises:
            None
        """
        # since the class is abstract we need to define a child class to be
        # able to instantiate it
        class Child(GuestSessionBase):
            """
            Concrete class of GuestSessionBase
            """
            def close(self, *args, **kwargs):
                super().close(*args, **kwargs)
            def run(self, *args, **kwargs):
                super().run(*args, **kwargs)
        self._child_cls = Child
    # setUp()

    def test_abstract_usage(self):
        """
        This is a very simple testcase which only validates if the class cannot
        be instantiated since it is abstract.

        Args:
            None

        Raises:
            AssertionError: if object instantiation does raise expected
                            exception
        """
        # pylint:disable=abstract-class-instantiated
        self.assertRaises(TypeError, GuestSessionBase)
    # test_abstract_usage()

    def test_methods(self):
        """
        Exercise all methods in the target class.

        Args:
            None

        Raises:
            AssertionError: if any assert call fails
        """
        session_obj = self._child_cls()

        # call each method and check if exception was raised
        methods = [
            ('close', ()),
            ('run', (None, None)),
        ]
        for method in methods:
            attr = getattr(session_obj, method[0])
            self.assertRaises(NotImplementedError, attr, *method[1])
    # test_methods()

# TestGuestSessionBase
