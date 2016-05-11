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
ZHmc module
@author: Felipe
@date: 18/07/2016
"""
#
# IMPORTS
#

from tessia_baselib.common.logger import getLogger
from tessia_baselib.hypervisors.hmc.zhmc.cpc import CPC
from tessia_baselib.hypervisors.hmc.zhmc.hmc_api_session import HmcApiSession
from tessia_baselib.hypervisors.hmc.zhmc.exceptions import ZHmcError


#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#


class ZHmc(object):

    """
    This class is responsible for creating a object abstracting for the HMC,
    according to the information passed as argument in the constructor.
    Additionally, it gets and stores in a dictionary the list of CPCs available
    to the user in the specific machine along with the corresponding URIs.
    """

    def __init__(self, host_name, user, passwd, port, timeout):
        """
        Constructor

        Args:
            host_name (str): hostname or ip address of system
            user (str): user to login to HMC
            passwd (str): password to login to HMC
            timeout (int): connection timeout

        Returns:
            None

        Raises:
            None
        """

        self.cpcs = None

        self._logger = getLogger(__name__)

        self.session = HmcApiSession(host_name, user, passwd, timeout, port)
        self.session.open_session()
    # __init__()

    def get_cpc(self, cpc_name):
        """
        This method returns the CPC class instance for given a cpc name.

        Args:
            cpc_name (str): name of the cpc whose class instance we want to
            retrieve.

        Returns:
            The cpc class instance

        Raises:
            ZHmcError:  if no CPC was found
        """

        if self.cpcs is None:
            self.cpcs = self.session.json_request(
                "GET",
                "/api/cpcs"
            )['cpcs']

        for cpc in self.cpcs:
            if cpc['name'] == cpc_name:
                return CPC(
                    self,
                    cpc['name'],
                    cpc['object-uri'],
                    cpc['status']
                )

        raise ZHmcError("CPC not found")
    # get_cpc()
# ZHmc
