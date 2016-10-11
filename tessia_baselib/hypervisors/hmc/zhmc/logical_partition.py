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
Logical Partition Abstraction
"""

#
# IMPORTS
#
from datetime import timedelta
from tessia_baselib.common.logger import get_logger
from tessia_baselib.hypervisors.hmc.zhmc.exceptions import ZHmcError

import time

#
# CONSTANTS AND DEFINITIONS
#

# default json request timeout (seconds)
DEFAULT_JSON_REQUEST_TIMEOUT = 60

#
# CODE
#
class LogicalPartition(object):

    """
    This class represents an abstraction for a Logical Partition (LPAR).
    """

    def __init__(self, hmc, lpar_name, lpar_uri, lpar_status):
        """
        Constructor

        Args:
            hmc (HmcApiSession): contains all the session information
            lpar_name (str): lpar name
            lpar_uri (str): lpar uri
            lpar_status (str): current lpar status

        Returns:
            None

        Raises:
            None
        """

        self._logger = get_logger(__name__)

        self.name = lpar_name
        self.uri = lpar_uri
        self._hmc = hmc
        self.status = lpar_status
    # __init__()

    def get_properties(self):
        """
        This method returns the LPAR's properties dictionary

        Args:
            None

        Returns:
            dict: logical partition properties

        Raises:
            None
        """

        properties = self._hmc.session.json_request(
            "GET",
            self.uri
        )

        return properties
    # get_properties()

    def activate(self, image_profile=None, force=False):
        """
        This method activates the lpar, putting it in a 'not-operating' status.

        Args:
            image_profile (str): image activation profile name. If not set, HMC
                                 will use the profile present in the parameter
                                 'next-activation-profile'
            force (bool): when true we have the right to force activation if
                          the partition is in "operating" status

        Returns:
            dict: contains what the hmc returns after executing the operation,
                  plus some info regarding the time needed to fulfill it

        Raises:
            None
        """

        param = dict()

        if force:
            param['force'] = force

        if image_profile is not None:
            param['activation-profile-name'] = image_profile

        job = self._issue_operation(
            "activate",
            timeout=DEFAULT_JSON_REQUEST_TIMEOUT,
            arg_dict=param
        )

        return job
    # activate()

    def deactivate(self, force=False):
        """
        This method deactivates the lpar, putting it in a 'not-activated'
        status.

        Args:
            force (bool): when true we have the right to force deactivation
                          if the partition is in "operating" status

        Returns:
            dict: contains what the hmc returns after executing the operation,
                  plus some info regarding the time needed to fulfill it

        Raises:
            None
        """

        param = dict()

        if force:
            param['force'] = force

        job = self._issue_operation(
            "deactivate",
            arg_dict=param,
            timeout=DEFAULT_JSON_REQUEST_TIMEOUT
        )

        return job
    # deactivate()

    def load(self, load_address, force=True):
        """
        This method is used to perform the operation of initial program load,
        or just load for short.

        Args:
            load_address (str): disk address to perform the IPL.
            force (bool): when true we have the right to force ipl if the
                          partition is in "operating" status

        Returns:
            dict: a dictionary that contains what the hmc returns after
                  executing the operation, plus some info regarding the time
                  needed to fulfill it

        Raises:
            None
        """
        param = dict()

        param['load-address'] = load_address

        if force:
            param['force'] = force

        job = self._issue_operation(
            "load",
            arg_dict=param,
            timeout=DEFAULT_JSON_REQUEST_TIMEOUT
        )

        return job
    # load()

    def scsi_load(self, load_address, wwpn, lun, force=False):
        """
        This method is used to perform the operation of initial program load,
        or just load for short, from a SCSI device.

        Args:
            load_address (str): address to perform the IPL.
            wwpn (str): worldwide port name (WWPN) of the target SCSI device to
                        be used for this operation, in hexadecimal.
            lun (str): hexadecimal logical unit number to be used for the SCSI
                       Load.
            force (bool): when true we have the right to force ipl if the
                          partition is in "operating" status

        Returns:
            dict: contains what the hmc returns after executing the operation,
                  plus some info regarding the time needed to fulfill it

        Raises:
            None
        """
        param = dict()

        param['load-address'] = load_address
        param['world-wide-port-name'] = wwpn
        param['logical-unit-number'] = lun

        if force:
            param['force'] = force

        job = self._issue_operation(
            "scsi-load",
            arg_dict=param,
            timeout=DEFAULT_JSON_REQUEST_TIMEOUT
        )

        return job
    # scsi_load()

    def stop(self):
        """
        This method is used to perform the 'stop' operation on a LPAR.
        The 'stop' operation stops the processors from processing instructions.

        Args:
            None

        Returns:
            dict: contains what the hmc returns after executing the operation,
                  plus some info regarding the time needed to fulfill it

        Raises:
            None
        """

        job = self._issue_operation(
            "stop",
            timeout=DEFAULT_JSON_REQUEST_TIMEOUT
        )

        return job
    # stop()

    def reset_clear(self, force=False):
        """
        This method is used to perform the 'reset-clear' operation on a LPAR.
        The Reset Clear operation initializes system or logical partition by
        clearing its pending interruptions, resetting its channel subsystem and
        resetting its processors. A reset prepares a system or logical
        partition for loading it with an operating system and clears main
        memory of the system or logical partition.

        Args:
            None

        Returns:
            job: contains what the hmc returns after executing the operation,
                 plus some info regarding the time needed to fulfill it

        Raises:
            None
        """
        param = dict()

        if force:
            param['force'] = force

        job = self._issue_operation(
            "reset-clear",
            arg_dict=param,
            timeout=DEFAULT_JSON_REQUEST_TIMEOUT
        )

        return job
    # reset_clear()

    def _issue_operation(self, operation, timeout, arg_dict=None):
        """
        Auxiliary method.
        Its role is to start the execution of the basic operations of an
        lpar that are asynchronous. The full list of the asynchronous
        operations can be found in the HMC Web Services documentation 2.13 or
        greater.

        Args:
            operation (str): name of the operation we want to issue, in
                             compliance with the Web Services documentation.
            timeout (int): how long we should wait for the asynchronous
                           operation to finish before raising an error.
            arg_dict (dict) : argument dictionary will take the place of the
                              body in the POST request if provided

        Returns:
            dict: contains what the hmc returns after executing the operation,
                  plus some info regarding the time needed to fulfill it

        Raises:
            ZHmcError: in case of timeout
        """
        start_status = self.status

        action = self.uri + "/operations/" + operation

        response = self._hmc.session.json_request(
            "POST",
            action,
            body=arg_dict
        )

        start_time = time.time()
        timeout_time = start_time + timeout
        while time.time() <= timeout_time:
            job = self._hmc.session.json_request(
                "GET",
                response['job-uri']
            )
            if job['status'] != 'running':
                break
            time.sleep(1)

        if job['status'] == 'running':
            raise ZHmcError(
                'Timeout value has been exceeded during ' + operation
            )

        self.status = self.get_properties()['status']
        end_status = self.status
        end_time = time.time()
        human_uptime = timedelta(seconds=int(end_time - start_time))

        jdict = dict()
        jdict['status-start'] = start_status
        jdict['status-end'] = end_status
        jdict['time-start'] = start_time
        jdict['time-end'] = end_time
        jdict['duration-formatted'] = str(human_uptime)

        return jdict
    # _issue_operation()
# LogicalPartition
