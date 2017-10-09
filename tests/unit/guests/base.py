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
Unit test for GuestBase
"""

#
# IMPORTS
#
from tessia_baselib.guests import base
from unittest import TestCase
from unittest.mock import sentinel

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

class TestGuestBase(TestCase):
    """
    Unit test for the GuestBase class
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
        class Child(base.GuestBase):
            """
            Concrete class of GuestBase
            """
            def hotplug(self, *args, **kwargs):
                super().hotplug(*args, **kwargs)
            def login(self, *args, **kwargs):
                super().login(*args, **kwargs)
            def logoff(self, *args, **kwargs):
                super().logoff(*args, **kwargs)
            def install_packages(self, *args, **kwargs):
                super().install_packages(*args, **kwargs)
            def open_session(self, *args, **kwargs):
                super().open_session(*args, **kwargs)
            def pull_file(self, *args, **kwargs):
                super().pull_file(*args, **kwargs)
            def push_file(self, *args, **kwargs):
                super().push_file(*args, **kwargs)
            def stop(self, *args, **kwargs):
                super().stop(*args, **kwargs)
        self._child_cls = Child
    # setUp()

    def test_attributes(self):
        """
        Testcase to exercise the attributes of the class. Verify if the
        attributes correspond to what was passed in the constructor.

        Args:
            None

        Raises:
            AssertionError: if an attribute does not match passed argument
        """
        self.assertRaises( # pylint:disable=abstract-class-instantiated
            TypeError,
            base.GuestBase,
            sentinel.system_name,
            sentinel.host_name,
            sentinel.user,
            sentinel.passwd,
            sentinel.extensions
        )

        # use sentinels for arguments to make sure we have the same value when
        # validating the object's attributes
        guest_obj = self._child_cls(
            sentinel.system_name,
            sentinel.host_name,
            sentinel.user,
            sentinel.passwd,
            sentinel.extensions
        )

        # validate attributes
        self.assertEqual('base', guest_obj.GUEST_ID)
        self.assertIs(sentinel.system_name, guest_obj.name)
        self.assertIs(sentinel.host_name, guest_obj.host_name)
        self.assertIs(sentinel.user, guest_obj.user)
        self.assertIs(sentinel.passwd, guest_obj.passwd)
        self.assertIs(sentinel.extensions, guest_obj.extensions)

    # test_attributes()

    def test_methods(self):
        """
        Testcase to exercise all the methods and attributes of the class. Since
        this is an abstract class we just validate if NotImplementError is
        raised after a call to each method.

        Args:
            None

        Raises:
            AssertionError: if guest object does not raise NotImplementedError
                            for the called methods
j       """
        # use sentinels for arguments to make sure we have the same value when
        # validating the object's attributes
        guest_obj = self._child_cls(
            sentinel.system_name,
            sentinel.host_name,
            sentinel.user,
            sentinel.passwd,
            sentinel.extensions
        )

        # call each method and check if exception was raised
        methods = [
            ('hotplug', (None, None, None, None)),
            ('login', ()),
            ('logoff', ()),
            ('install_packages', (None,)),
            ('open_session', ()),
            ('pull_file', ()),
            ('push_file', (None, None, None)),
            ('stop', ()),
        ]
        for method in methods:
            attr = getattr(guest_obj, method[0])
            self.assertRaises(NotImplementedError, attr, *method[1])

    # test_methods()

# TestGuestBase
