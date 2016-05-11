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
Implementation of hypervisor interface for HMC
"""

#
# IMPORTS
#

from tessia_baselib.common.logger import getLogger
from tessia_baselib.common.params_validators.utils  import validate_params
from tessia_baselib.hypervisors.base import HypervisorBase
from tessia_baselib.hypervisors.hmc.zhmc.zhmc import ZHmc
from tessia_baselib.hypervisors.hmc.zhmc.exceptions import ZHmcError


#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

# pylint:disable=abstract-method
class HypervisorHmc(HypervisorBase):
    """
    This class implements the driver to support the HMC hypervisor type
    """

    # the identifier for this hypervisor class
    HYP_ID = 'hmc'

    def __init__(self, system_name, host_name, user, passwd, parameters):
        """
        Constructor, store instance values via base class and initialize logger

        Args:
            system_name (str): string containing the hypervisor name
            host_name (str): hostname or ip address of system
            user (str): user to login to HMC
            passwd (str): password to login to HMC
            parameters (dict): A dictionary containing values specific to each
            hypervisor type

        Returns:
            None

        Raises:
            None
        """
        # base class will store instances values
        super().__init__(
            system_name,
            host_name,
            user,
            passwd,
            parameters
        )

        # HMC session variable to be initialized by login()
        self._session = None

        # initialize logger object
        self._logger = getLogger(__name__)

        self._logger.debug(
            "create HypervisorHMC: name='%s' host_name='%s' user='%s' "
            "parameters='%s'",
            self.name,
            self.host_name,
            self.user,
            str(self.parameters)
        )
    # __init__()

    def login(self, timeout=60):
        """
        Execute the login to the HMC using the credentials
        provided.

        Args:
            timeout (int): how long in seconds to wait for connection

        Returns:
            None

        Raises:
            None
        """
        self._logger.debug(
            "performing LOGIN HypervisorHMC: name='%s' host_name='%s' "
            "user='%s' parameters='%s'",
            self.name,
            self.host_name,
            self.user,
            str(self.parameters)
        )

        if self._session is not None:
            self._logger.warning(
                "Login called with connection already active:"
                " dropping previous connection object"
            )

        self._session = ZHmc(
            self.host_name,
            self.user,
            self.passwd,
            self.parameters.get('port'),
            timeout
        )

    # login()

    def logoff(self):
        """
        Close an active connection to the HMC

        Args:
            None

        Returns:
            None

        Raises:
            ZHmcError if the operation is performed without previous login
        """
        self._logger.debug(
            "performing LOGOFF HypervisorHMC: name='%s' host_name='%s' "
            "user='%s' parameters='%s'",
            self.name,
            self.host_name,
            self.user,
            str(self.parameters)
        )
        if self._session is None:
            raise ZHmcError("You need to login first.")

        self._session.session.close_session()
        self._session = None
    # logoff()

    @validate_params
    def start(self, guest_name, cpu, memory, parameters):

        """
        Activate (If necessary) and IPL a target LPAR

        Args:
            guest_name (str): LPAR name.
            cpu (int): number of CPU's to assign.
            memory (int): amount of memory to assin in megabytes.
            parameters (dict): content specific to each hypervisor type. In
            this case, it contains the CPC name and boot type configuration

        Returns:
            None

        Raises:
            ZHmcError if the operation is performed without previous login
        """

        self._logger.debug(
            "performing START HypervisorHMC: name='%s' host_name='%s' "
            "user='%s' parameters='%s'",
            self.name,
            self.host_name,
            self.user,
            str(self.parameters)
        )

        if self._session is None:
            raise ZHmcError("You need to login first")

        cpc = self._session.get_cpc(parameters.get('cpc_name'))
        lpar = cpc.get_lpar(guest_name)
        # The profiles have the same name as the LPAR's
        image_profile = cpc.get_image_profile(guest_name)

        # Calculating the number of processors chosen
        args = self._calculate_number_cpus(cpu, parameters.get('ifl_cpus', 0))
        # Set storage
        args['mem'] = memory

        try:
            update = self._update_resources(args, image_profile)

            if update:
            # If we update the resouces, we need to activate the LPAR again so
            # changes can take effect, no matter LPAR current state
                lpar.activate(force=True)
            else:
                # If lpar is already activated, we skip the activation step
                if lpar.status == 'not-activated':
                    lpar.activate()

            # SCSI Load
            if parameters.get('boot_params').get('boot_method') == 'scsi':
                lpar.scsi_load(
                    parameters.get('boot_params').get('iface_devicenr'),
                    parameters.get('boot_params').get('wwpn'),
                    parameters.get('boot_params').get('lun')
                )
            else:
            # DASD Load
                lpar.load(parameters.get('boot_params').get('devicenr'))
        except:
            if update:
                # At this point I believe it is safer to leave the image
                # status as a user responsability
                self._logger.debug(
                    "An error ocurred, should we roll back?"
                )
            raise
    # start()

    def _calculate_number_cpus(self, total_cpus, ifl_cpus):
        """
        Auxiliary method. If the number of IFL's are specified, it is necessary
        to calculate how many CP's need to be set following the equation:
            CP = Total - IFL

        Args:
            total_cpus (int): total number of cpus
            ifl_cpus (int): number of IFL cpus

        Returns:
            args (dict): number of cpu/ifl.

        Raises:
            None
        """
        args = dict()

        # If the number of IFL's are specified, we need to calculate how
        # many CP's are to be used.
        cp_cpus = total_cpus - ifl_cpus
        args['cp'] = cp_cpus
        args['ifl'] = ifl_cpus

        self._logger.debug("Number of cpus calculted: args='%s'", args)

        return args
    # _calculate_number_cpus()

    def _update_resources(self, args, image_profile):
        """
        Auxiliary method. If resources are different, we need to change the
        HMC profile before performing the LOAD, otherwise the amout of memory
        or cpus will not change.

        Args:
            image_profile (ActivationProfile): ActivationProfile object that
            represents an image profile

        Returns:
            Boolean: true if resources were updated, else otherwise

        Raises:
            None
        """

        img_properties = image_profile.get_properties()

        body = dict()

        update = False

        if img_properties['central-storage'] != args['mem']:
            body['central-storage'] = args['mem']
            update = True

        if (img_properties['number-shared-general-purpose-processors']
                != args['cp']):
            body['number-shared-general-purpose-processors'] = args['cp']
            update = True

        if (img_properties['number-shared-ifl-processors']
                != args['ifl']):
            body['number-shared-ifl-processors'] = args['ifl']
            update = True

        # Update the image profile with the new config if it is different
        # from what it is already in the HMC
        if update:
            self._logger.debug(
                "Updating image profile: args='%s'", body
            )
            image_profile.update(body)

        return update
    # _update_resources()

    @validate_params
    def stop(self, guest_name, parameters):
        """
        Deactivate a target LPAR

        Args:
            guest_name (str): target LPAR name.
            parameters (dict): content specific to each hypervisor type.
            In this case, the CPC name.

        Returns:
            None

        Raises:
            ZHmcError: if session is not created
                       if LPAR status is different from 'operating'
        """

        if self._session is None:
            raise ZHmcError("You need to login first")

        self._logger.debug(
            "performing STOP HypervisorHMC: name='%s' host_name='%s' "
            "user='%s' parameters='%s'",
            self.name,
            self.host_name,
            self.user,
            str(self.parameters)
        )
        cpc = self._session.get_cpc(parameters.get('cpc_name'))
        lpar = cpc.get_lpar(guest_name)

        if lpar.status != 'operating':
            raise ZHmcError(
                "Operation not allowed on LPAR with status '%s'" % lpar.status
            )

        lpar.stop()
        lpar.reset_clear()
    # stop()

    def reboot(self, guest_name, parameters):
        """
        Reboot a target LPAR

        Args:
            guest_name (str): target LPAR name.
            parameters (dict): content specific to each hypervisor type.
            In this case, the CPC name.

        Returns:
            None

        Raises:
            NotImplementedError
        """
        self._logger.debug(
            "Method not implemented: args='%s','%s'", guest_name, parameters
        )

        raise NotImplementedError()
    # reboot()
# HypervisorHmc
