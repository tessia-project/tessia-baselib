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
Unit test for HypervisorBase
"""

#
# IMPORTS
#
from tessia.baselib.hypervisors import base
from unittest import TestCase
from unittest.mock import sentinel

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

class TestHypervisorBase(TestCase):
    """
    Unit test for the HypervisorBase class
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
        class Child(base.HypervisorBase):
            """
            Concrete class of HypervisorBase
            """
            def login(self, timeout=60):
                super().login(timeout=timeout)
            def logoff(self):
                super().logoff()
            def reboot(self, guest_name, parameters):
                super().reboot(guest_name, parameters)
            def start(self, guest_name, cpu, memory, parameters):
                super().start(guest_name, cpu, memory, parameters)
            def stop(self, guest_name, parameters):
                super().stop(guest_name, parameters)
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
        # pylint:disable=abstract-class-instantiated
        self.assertRaises(
            TypeError,
            base.HypervisorBase,
            sentinel.system_name,
            sentinel.host_name,
            sentinel.user,
            sentinel.passwd,
            sentinel.parameters
        )


        # use sentinels for arguments to make sure we have the same value when
        # validating the object's attributes
        guest_obj = self._child_cls(
            sentinel.system_name,
            sentinel.host_name,
            sentinel.user,
            sentinel.passwd,
            sentinel.parameters
        )

        # validate attributes
        self.assertEqual('base', guest_obj.HYP_ID)
        self.assertIs(sentinel.system_name, guest_obj.name)
        self.assertIs(sentinel.host_name, guest_obj.host_name)
        self.assertIs(sentinel.user, guest_obj.user)
        self.assertIs(sentinel.passwd, guest_obj.passwd)
        self.assertIs(sentinel.parameters, guest_obj.parameters)

        # test when parameters is None
        guest_obj = self._child_cls(
            sentinel.system_name,
            sentinel.host_name,
            sentinel.user,
            sentinel.passwd,
            None,
        )
        self.assertEqual({}, guest_obj.parameters)
    # test_attributes()

    def test_methods(self):
        """
        Testcase to exercise all the methods and attributes of the class. Since
        this is an abstract class we just validate if NotImplementError is
        raised after a call to each method.

        Args:
            None

        Raises:
            AssertionError: if hypervisor object does not raise
                            NotImplementedError for the called methods
        """
        # use sentinels for arguments to make sure we have the same value when
        # validating the object's attributes
        hyp_obj = self._child_cls(
            sentinel.system_name,
            sentinel.host_name,
            sentinel.user,
            sentinel.passwd,
            sentinel.parameters
        )

        # call each method and check if exception was raised
        methods = [
            ('login', ()),
            ('logoff', ()),
            ('reboot', (None, None,)),
            ('start', (None, None, None, None,)),
            ('stop', (None, None)),
            ('reboot', (None, None)),
        ]
        for method in methods:
            attr = getattr(hyp_obj, method[0])
            self.assertRaises(NotImplementedError, attr, *method[1])
    # test_methods()

# TestHypervisorBase
