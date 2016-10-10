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
Activation Profile Abstraction
"""

#
# IMPORTS
#

from tessia_baselib.common.logger import get_logger

#
# CONSTANTS AND DEFINITIONS
#


#
# CODE
#


class ActivationProfile(object):

    """
    This class is responsible for creating the Activation Profile abstraction.
    It represents one of the possible types of activation profiles available
    at the HMC: Image, Load, Reset or Group
    """

    def __init__(self, hmc, profile_name, profile_uri, profile_type):
        """
        Constructor

        Args:
            hmc (HmcApiSession): contains all the session information
            profile_name (str): profile name
            profile_uri (str): the profile URI on the HMC
            profile_type (str): the profile type we are referencing:
                                'image', 'load', 'reset' or 'group'

        Returns:
            None

        Raises:
            None
        """

        self._logger = get_logger(__name__)

        self.name = profile_name
        self.uri = profile_uri
        self.type = profile_type
        self._hmc = hmc
    # __init__()

    def get_properties(self):
        """
        Return current Activation Profile properties dictionary.

        Args:
            None

        Returns:
            dict: image profile properties

        Raises:
            None
        """

        properties = self._hmc.session.json_request(
            "GET",
            self.uri
        )
        return properties
    # get_properties

    def update(self, param):
        """
        This method updates the current ActivationProfile. Please refer to
        HMC API Documentation version 2.13.1 or later in order to set the right
        parameters. The basic parameters for this module are:
        Image Activation Profile:
            'central-storage' - Total memory of the LPAR
            'number-shared-general-purpose-processors' - Number of CP's
            'number-shared-ifl-processors' - Number of IFL's
        Load Activation Profile:
            TODO
        Reset Activation Profile:
            TODO
        Group Activation Profile:
            TODO

        Args:
            None

        Returns:
            None

        Raises:
            None
        """

        self._hmc.session.json_request(
            "POST",
            self.uri,
            body=param
        )
    # update()
# ActivationProfile
