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
from unittest import TestCase
from unittest.mock import Mock
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

        Returns:
            None

        Raises:
            None
        """

        # for tests it is preferrable to import the module and class here
        # because we might need to patch something first
        from tessia_baselib.hypervisors import base
        self.hypModule = base

    # setUp()

    def test_attributes(self):
        """
        Testcase to exercise the attributes of the class. Verify if the
        attributes correspond to what was passed in the constructor.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if an attribute does not match passed argument
        """
        # use sentinels for arguments to make sure we have the same value when
        # validating the object's attributes
        guestObj = self.hypModule.HypervisorBase(
            sentinel.logger,
            sentinel.system_name,
            sentinel.host_name,
            sentinel.user,
            sentinel.passwd,
            sentinel.extensions
        )

        # validate attributes
        self.assertEqual('base', guestObj.hyp_id)
        self.assertIs(sentinel.logger, guestObj.logger)
        self.assertIs(sentinel.system_name, guestObj.name)
        self.assertIs(sentinel.host_name, guestObj.host_name)
        self.assertIs(sentinel.user, guestObj.user)
        self.assertIs(sentinel.passwd, guestObj.passwd)
        self.assertIs(sentinel.extensions, guestObj.extensions)

    # test_attributes()

    def test_methods(self):
        """
        Testcase to exercise all the methods and attributes of the class. Since
        this is an abstract class we just validate if NotImplementError is
        raised after a call to each method.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if hypervisor object does not raise
                            NotImplementedError for the called methods
        """
        # use sentinels for arguments to make sure we have the same value when
        # validating the object's attributes
        hypervisorObj = self.hypModule.HypervisorBase(
            sentinel.logger,
            sentinel.system_name,
            sentinel.host_name,
            sentinel.user,
            sentinel.passwd,
            sentinel.extensions
        )

        # call each method and check if exception was raised
        # login method
        self.assertRaises(NotImplementedError, hypervisorObj.login)
        # logoff method
        self.assertRaises(NotImplementedError, hypervisorObj.logoff)
        # start method
        with self.assertRaises(NotImplementedError):
            hypervisorObj.start('guestfoo', {}, 'methodfoo', 'devicefoo', {})
        # stop method
        with self.assertRaises(NotImplementedError):
            hypervisorObj.stop('guestfoo', {})

    # test_methods()

# TestGuestBase
