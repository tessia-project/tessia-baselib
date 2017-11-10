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
CPC Abstraction
"""

#
# IMPORTS
#

from tessia.baselib.common.logger import get_logger
from tessia.baselib.hypervisors.hmc.zhmc.exceptions import ZHmcError
from tessia.baselib.hypervisors.hmc.zhmc.logical_partition import \
    LogicalPartition
from tessia.baselib.hypervisors.hmc.zhmc.activation_profile import \
    ActivationProfile


#
# CONSTANTS AND DEFINITIONS
#


#
# CODE
#
class CPC(object):

    """
    This class represents an abstraction for a CPC.
    """

    def __init__(self, hmc, cpc_name, cpc_uri, cpc_status):
        """
        Constructor

        Args:
            hmc (HmcApiSession): contains all the session information
            cpc_name (str):   cpc name
            cpc_uri (str):    cpc uri
            cpc_status (str): current cpc status

        Raises:
            None
        """

        self._logger = get_logger(__name__)

        self.name = cpc_name
        self.uri = cpc_uri
        self.status = cpc_status
        self._hmc = hmc

        self._lpars = None
        self._image_profiles = None
        self._load_profiles = None
        self._reset_profiles = None
        self._group_profiles = None

    # __init__()

    def get_properties(self):
        """
        This method returns the CPC's properties dictionary.

        Args:
            None

        Returns:
            dict: CPC properties

        Raises:
            None
        """

        properties = self._hmc.session.json_request(
            "GET",
            self.uri
        )

        return properties
    # get_properties()

    def get_lpar(self, lpar_name):
        """
        This method returns a LPAR class instance for a given lpar name

        Args:
            lpar_name (str): LPAR name

        Returns:
            LogicalPartition: the LPAR class instance

        Raises:
            ZHmcError: if LPAR was not found
        """

        # Retrieve all lpars associated with the current CPC
        if self._lpars is None:
            action = str(self.uri) + "/logical-partitions"
            self._lpars = self._hmc.session.json_request(
                "GET",
                action
            )["logical-partitions"]

        # Retrieve the lpar URI and status
        for lpar in self._lpars:
            if lpar['name'] == lpar_name:
                return LogicalPartition(
                    self._hmc,
                    lpar['name'],
                    lpar['object-uri'],
                    lpar['status']
                )

        raise ZHmcError("LPAR '%s' not found" % lpar_name)
    # get_lpar()

    def get_load_profile(self, load_profile_name):
        """
        This method returns a Load Activation Profile class instance for a
        given profile name

        Args:
            load_profile_name (str): load profile name

        Returns:
            ActivationProfile: the Load Activation Profile instance

        Raises:
            ZHmcError: if load profile was not found
        """

        if self._load_profiles is None:
            action = str(self.uri) + "/load-activation-profiles"
            self._load_profiles = self._hmc.session.json_request(
                "GET",
                action
            )["load-activation-profiles"]

        for load_profile in self._load_profiles:
            if load_profile['name'] == load_profile_name:
                return ActivationProfile(
                    self._hmc,
                    load_profile['name'],
                    load_profile['element-uri'],
                    "load"
                )

        raise ZHmcError(
            "Load Activation Profile '%s' not found" % load_profile_name
        )
    # get_load_profile()

    def get_image_profile(self, image_profile_name):
        """
        This method returns an Image Activation Profile class instance for a
        given image profile name

        Args:
            image_profile_name (str):  image profile name

        Returns:
            ActivationProfile: the Image Activation Profile instance

        Raises:
            ZHmcError: if image profile was not found
        """

        if self._image_profiles is None:
            action = str(self.uri) + "/image-activation-profiles"
            self._image_profiles = self._hmc.session.json_request(
                "GET",
                action
            )["image-activation-profiles"]

        for image_profile in self._image_profiles:
            if image_profile['name'] == image_profile_name:
                return ActivationProfile(
                    self._hmc,
                    image_profile['name'],
                    image_profile['element-uri'],
                    "image"
                )

        raise ZHmcError(
            "Image Activation Profile '%s' not found" % image_profile_name
        )
    # get_image_profile()

    def get_reset_profile(self, reset_profile_name):
        """
        This method returns a Reset Activation Profile class instance for a
        give reset profile name.

        Args:
            reset_profile_name (str): reset profile name

        Raises:
            NotImplementedError: as it needs implementation
        """
        # TODO: implement feature
        self._logger.debug(
            "Method not implemented: args='%s'", reset_profile_name
        )

        raise NotImplementedError()
    # get_reset_profile()

    def get_group_profile(self, group_profile_name):
        """
        This method returns a Group Activation Profile class instance for a
        given group profile name

        Args:
            group_profile_name (str):  group profile name

        Raises:
            NotImplementedError: as it needs implementation
        """
        # TODO: implement feature
        self._logger.debug(
            "Method not implemented: args='%s'", group_profile_name
        )

        raise NotImplementedError()
    # get_group_profile()
# CPC
