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
from tessia_baselib.hypervisors.hmc.zhmc.cpc import CPC
from tessia_baselib.hypervisors.hmc.zhmc.exceptions import ZHmcError
from tessia_baselib.hypervisors.hmc.zhmc.logical_partition import LogicalPartition
from tessia_baselib.hypervisors.hmc.zhmc.activation_profile import (
    ActivationProfile
)


#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#


class TestCPC(TestCase):
    def setUp(self):
        """
        Setup a CPC object.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        hmc_object = mock.Mock()
        cpc_name = 'dummy_name'
        cpc_uri = 'dummy.domain.com'
        cpc_status = 'dummy_status'
        self.cpc = CPC(
            hmc_object,
            cpc_name,
            cpc_uri,
            cpc_status
        )

        # validate if attributes were correctly assigned to object
        self.assertEqual(hmc_object, self.cpc._hmc)
        self.assertEqual(cpc_name, self.cpc.name)
        self.assertEqual(cpc_uri, self.cpc.uri)
        self.assertEqual(cpc_status, self.cpc.status)
        self.assertIs(None, self.cpc._lpars)
        self.assertIs(None, self.cpc._image_profiles)
        self.assertIs(None, self.cpc._load_profiles)
        self.assertIs(None, self.cpc._group_profiles)
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
        session = self.cpc._hmc.session
        session.json_request.return_value = fake_response

        prop = self.cpc.get_properties()

        # asserts
        self.assertEqual(prop, fake_response)
        session.json_request.assert_called_with(
            "GET",
            self.cpc.uri
        )
    # test_get_properties()

    def test_get_lpar(self):
        """
        Test if get_lpar() method work as expected.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """

        fake_response = {
            'logical-partitions':
            [
                {
                    'name': 'dummy_lpar',
                    'object-uri': 'dummy.com',
                    'status': 'dummy_status'
                }
            ]
        }

        session = self.cpc._hmc.session
        session.json_request.return_value = fake_response

        lpar = self.cpc.get_lpar('dummy_lpar')
        self.assertIsInstance(lpar, LogicalPartition)
        self.assertEqual(lpar.name, 'dummy_lpar')
        self.assertEqual(lpar.uri, 'dummy.com')
        self.assertEqual(lpar.status, 'dummy_status')

        # check if error is raised when no lpar was found
        self.cpc._lpars = [{'name': 'different_name'}]
        with self.assertRaises(ZHmcError):
            self.cpc.get_lpar('dummy_lpar')
    # test_get_lpar()

    def test_get_load_profile(self):
        """
        Test if get_load_profile() method work as expected.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """

        fake_response = {
            'load-activation-profiles':
            [
                {
                    'name': 'dummy_profile',
                    'element-uri': 'dummy.com'
                }
            ]
        }

        session = self.cpc._hmc.session
        session.json_request.return_value = fake_response

        profile = self.cpc.get_load_profile('dummy_profile')
        self.assertIsInstance(profile, ActivationProfile)
        self.assertEqual(profile.name, 'dummy_profile')
        self.assertEqual(profile.uri, 'dummy.com')
        self.assertEqual(profile.type, 'load')


        # check if error is raised when no lpar was found
        self.cpc._load_profiles = [{'name': 'different_name'}]
        with self.assertRaises(ZHmcError):
            self.cpc.get_load_profile('dummy_profile')
    # test_get_load_profile()

    def test_get_image_profile(self):
        """
        Test if get_image_profile() method work as expected.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """

        fake_response = {
            'image-activation-profiles':
            [
                {
                    'name': 'dummy_profile',
                    'element-uri': 'dummy.com'
                }
            ]
        }

        session = self.cpc._hmc.session
        session.json_request.return_value = fake_response

        profile = self.cpc.get_image_profile('dummy_profile')
        self.assertIsInstance(profile, ActivationProfile)
        self.assertEqual(profile.name, 'dummy_profile')
        self.assertEqual(profile.uri, 'dummy.com')
        self.assertEqual(profile.type, 'image')


        # check if error is raised when no lpar was found
        self.cpc._image_profiles = [{'name': 'different_name'}]
        with self.assertRaises(ZHmcError):
            self.cpc.get_image_profile('dummy_profile')
    # test_get_image_profile()

    def test_get_reset_profile(self):
        """
        Test if get_reset_profile() method work as expected.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        with self.assertRaises(NotImplementedError):
            self.cpc.get_reset_profile('dummy_profile')
    # test_get_reset_profile()

    def test_get_group_profile(self):
        """
        Test if get_group_profile() method work as expected.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: if validation fails
        """
        with self.assertRaises(NotImplementedError):
            self.cpc.get_group_profile('dummy_profile')
    # test_get_group_profile()
