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

# pylint: disable=all

#
# IMPORTS
#

from unittest import mock
from unittest import TestCase
from unittest.mock import patch
from tessia_baselib.hypervisors.hmc.zhmc.activation_profile import (
    ActivationProfile
)

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#


class TestActivationProfile(TestCase):
    def setUp(self):
        """
        Setup a Activation Profile object.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        hmc_object = mock.Mock()
        profile_name = 'dummy_name'
        profile_uri = 'dummy.domain.com'
        profile_type = 'dummy_type'
        self.activation_profile = ActivationProfile(
            hmc_object,
            profile_name,
            profile_uri,
            profile_type
        )

        # validate if attributes were correctly assigned to object
        self.assertEqual(hmc_object, self.activation_profile._hmc)
        self.assertEqual(profile_name, self.activation_profile.name)
        self.assertEqual(profile_uri, self.activation_profile.uri)
        self.assertEqual(profile_type, self.activation_profile.type)
    # setUp()

    def test_get_properties(self):
        """
        Test if get_properties() method work as expected.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        # set fake response
        fake_response = {'status': 'dummy_status'}
        session = self.activation_profile._hmc.session
        session.json_request.return_value = fake_response

        prop = self.activation_profile.get_properties()

        # asserts
        self.assertEqual(prop, fake_response)
        session.json_request.assert_called_with(
            "GET",
            self.activation_profile.uri
        )
    # test_get_properties()

    def test_update(self):
        """
        Test if update() method work as expected.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        # set fake dictionario
        fake_dict = {'status': 'dummy_status'}

        prop = self.activation_profile.update(fake_dict)

        # asserts
        session = self.activation_profile._hmc.session
        session.json_request.assert_called_with(
            "POST",
            self.activation_profile.uri,
            body=fake_dict
        )
    # test_update()
