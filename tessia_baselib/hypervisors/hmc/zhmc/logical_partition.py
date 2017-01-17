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
from tessia_baselib.hypervisors.hmc.zhmc.exceptions import ZHmcRequestError

import time

#
# CONSTANTS AND DEFINITIONS
#

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

    def _wait_for_job(self, job_uri, timeout):
        """
        Wait for a given job to be completed, based on the provided timeout.

        Args:
            job_uri (str): url to use to query API for the job status
            timeout (int): timeout in seconds to wait until job finishes

        Raises:
            ZHmcRequestError: in case timeout is reached
        """
        # asynchronous operation: do not wait for job completion
        if timeout <= 0:
            return

        timeout_date = time.time() + timeout
        while True:
            time.sleep(1)
            job_dict = self._hmc.session.json_request("GET", job_uri)
            if job_dict['status'] == 'complete':
                break
            elif time.time() >= timeout_date:
                raise ZHmcRequestError(
                    'Timed out while waiting for load job completion')
    # _wait_for_job()

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

    def activate(self, image_profile=None):
        """
        This method activates the lpar, putting it in a 'not-operating' status.

        Args:
            image_profile (str): image activation profile name. If not set, HMC
                                 will use the profile present in the parameter
                                 'next-activation-profile'

        Returns:
            dict: contains what the hmc returns after executing the operation,
                  plus some info regarding the time needed to fulfill it

        Raises:
            None
        """

        param = dict()
        param['force'] = True

        if image_profile is not None:
            param['activation-profile-name'] = image_profile

        job = self._issue_operation(
            "activate",
            arg_dict=param
        )

        return job
    # activate()

    def deactivate(self):
        """
        This method deactivates the lpar, putting it in a 'not-activated'
        status.

        Args:
            None

        Returns:
            dict: contains what the hmc returns after executing the operation,
                  plus some info regarding the time needed to fulfill it

        Raises:
            None
        """

        param = dict()
        param['force'] = True

        job = self._issue_operation(
            "deactivate",
            arg_dict=param
        )

        return job
    # deactivate()

    def load(self, load_address, timeout=0):
        """
        This method is used to perform the operation of initial program load,
        or just load for short.

        Args:
            load_address (str): disk address to perform the IPL.
            timeout (int): how long to wait for job completion, a value equal
                or less than 0 means to operate asynchronously (the default)

        Returns:
            dict: containing key 'job-uri' to retrieve job status

        Raises:
            ZHmcRequestError: if timed out while waiting for job completion
        """
        param = dict()

        param['load-address'] = load_address
        param['force'] = True

        load_resp = self._issue_operation(
            "load",
            arg_dict=param
        )

        self._wait_for_job(load_resp['job-uri'], timeout)

        return load_resp
    # load()

    def scsi_load(self, load_address, wwpn, lun, timeout=0):
        """
        This method is used to perform the operation of initial program load,
        or just load for short, from a SCSI device.

        Args:
            load_address (str): address to perform the IPL.
            wwpn (str): worldwide port name (WWPN) of the target SCSI device to
                        be used for this operation, in hexadecimal.
            lun (str): hexadecimal logical unit number to be used for the SCSI
                       Load.
            timeout (int): how long to wait for job completion, a value equal
                or less than 0 means to operate asynchronously (the default)

        Returns:
            dict: containing key 'job-uri' to retrieve job status

        Raises:
            None
        """
        param = dict()

        param['load-address'] = load_address
        param['world-wide-port-name'] = wwpn
        param['logical-unit-number'] = lun
        param['force'] = True

        load_resp = self._issue_operation(
            "scsi-load",
            arg_dict=param
        )

        self._wait_for_job(load_resp['job-uri'], timeout)

        return load_resp
    # scsi_load()

    def send_os_command(self, command):
        """
        This method is used to perform the operation of initial program load,
        or just load for short, from a SCSI device.

        Args:
            command (str): linux command

        Returns:
            dict: contains what the hmc returns after executing the operation,
                  plus some info regarding the time needed to fulfill it

        Raises:
            None
        """
        param = dict()
        param['operating-system-command-text'] = command

        job = self._issue_operation(
            "send-os-cmd",
            arg_dict=param
        )

        return job
    # send_os_command()

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

        job = self._issue_operation("stop")

        return job
    # stop()

    def reset_clear(self):
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
        param['force'] = True

        job = self._issue_operation(
            "reset-clear",
            arg_dict=param
        )

        return job
    # reset_clear()

    def _issue_operation(self, operation, arg_dict=None):
        """
        Auxiliary method.
        Its role is to start the execution of the basic operations of an
        lpar that are asynchronous. The full list of the asynchronous
        operations can be found in the HMC Web Services documentation 2.13 or
        greater.

        Args:
            operation (str): name of the operation we want to issue, in
                             compliance with the Web Services documentation.
            arg_dict (dict) : argument dictionary will take the place of the
                              body in the POST request if provided

        Returns:
            dict: contains what the hmc returns after executing the operation,
                  plus some info regarding the time needed to fulfill it

        Raises:
            ZHmcError: in case of timeout
        """
        start_time = time.time()

        action = self.uri + "/operations/" + operation

        job_dict = self._hmc.session.json_request(
            "POST",
            action,
            body=arg_dict
        )

        end_time = time.time()
        human_uptime = timedelta(seconds=int(end_time - start_time))

        job_dict['time-start'] = start_time
        job_dict['time-end'] = end_time
        job_dict['duration-formatted'] = str(human_uptime)

        return job_dict
    # _issue_operation()
# LogicalPartition
