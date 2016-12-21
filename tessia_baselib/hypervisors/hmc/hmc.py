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

from tessia_baselib.config import CONF
from tessia_baselib.common.logger import get_logger
from tessia_baselib.guests.linux.linux import GuestLinux
from tessia_baselib.hypervisors.hmc.zhmc.zhmc import ZHmc
from tessia_baselib.hypervisors.base import HypervisorBase
from tessia_baselib.hypervisors.hmc.zhmc.exceptions import ZHmcError
from tessia_baselib.common.params_validators.utils import validate_params

import time
#
# CONSTANTS AND DEFINITIONS
#

NETBOOT_LOAD_TIMEOUT = 30 # seconds
NETBOOT_USER = "root"
NETBOOT_PASSWORD = "somepasswd"

#
# CODE
#

class HypervisorHmc(HypervisorBase):
    """
    This class implements the driver to support the HMC hypervisor type
    """

    # the identifier for this hypervisor class
    HYP_ID = 'hmc'

    def __init__(self, system_name, host_name, user, passwd, parameters=None):
        """
        Constructor, store instance values via base class and initialize logger

        Args:
            system_name (str): string containing the hypervisor name
            host_name (str): hostname or ip address of system
            user (str): user to login to HMC
            passwd (str): password to login to HMC
            parameters (dict): values specific to each hypervisor type

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
        self._logger = get_logger(__name__)

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
            ZHmcError: if the operation is performed without previous login
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
            memory (int): amount of memory to assign in megabytes.
            parameters (dict): contains the CPC name and boot type config

        Returns:
            None

        Raises:
            ZHmcError: if the operation is performed without previous login
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
        # Profiles have the same name as the LPAR's
        image_profile = cpc.get_image_profile(guest_name)

        # Calculating the number of processors chosen
        args = self._calculate_number_cpus(cpu, parameters.get('ifl_cpus', 0))
        # Set storage
        args['mem'] = memory

        try:
            update = self._update_resources(args, image_profile)

            # image profile updated: we need to activate the LPAR again so
            # changes can take effect
            if update or lpar.status == 'not-activated':
                lpar.activate()

            if parameters.get('boot_params').get('boot_method') == 'scsi':
                # SCSI Load
                lpar.scsi_load(
                    parameters.get('boot_params').get('zfcp_devicenr'),
                    parameters.get('boot_params').get('wwpn'),
                    parameters.get('boot_params').get('lun')
                )
            elif parameters.get('boot_params').get('boot_method') == 'dasd':
                # DASD Load
                lpar.load(parameters.get('boot_params').get('devicenr'))
            else:
                # Network
                # The netboot is performed using a a custom ramdisk.
                # Once the ramdisk is loaded, we configure the network
                # using the SEND_OS_CMD, connect throught SSH, copy the files
                # to the host and execute the kexec to load the kernel the user
                # specified in the parameters.
                # The HMC API does not support Boot From Removable Media
                # like in the UI, so this is a workaround.

                # retrieve the netboot disk
                disks = CONF.get_config()['netdisks']

                # load and wait operation to finish
                lpar.load(disks[cpc.name])

                start = time.time()
                timeout = start + NETBOOT_LOAD_TIMEOUT
                while lpar.get_properties()['status'] != 'operating' and \
                      start <= timeout:
                    time.sleep(1)
                    start += 1
                if start >= timeout:
                    raise Exception(
                        "Problem while performing load on netboot disk"
                    )

                time.sleep(5) # wait 5 seconds to make sure prompt is ready

                # enable ramdisk network
                self._setup_ramdisk_network(
                    parameters.get('boot_params'), lpar
                )

                # FIXME
                # There is a a very known issue that happens once in a while
                # that causes LPAR's to be unreachable in the network until a
                # ping is performed (probably to update some arp table or so).
                # Once this issue is fixed, remove this.
                lpar.send_os_command(
                    "ping -c 1 {}".format(
                        parameters.get('boot_params').get('gateway')
                    )
                )

                guest = GuestLinux(
                    lpar.name,
                    parameters.get('boot_params').get('ip'),
                    NETBOOT_USER,
                    NETBOOT_PASSWORD,
                    {}
                )

                guest.login()
                self._execute_kexec(guest, parameters.get('boot_params'))
                guest.logoff()

        except Exception as exc:
            self._logger.debug(
                'An error ocurred during start, info:', exc_info=True)
            raise ZHmcError('Operation failed with: {}'.format(str(exc)))
    # start()

    def _execute_kexec(self, guest, boot_params):
        """
        Auxiliary method. Execute kexec command on target host.
        This method is only used for the network boot method.

        Args:
            guest (GuestLinux): guest linux object
            boot_params (dict): dictionary with boot parameters

        Returns:
            None

        Raises:
            None
        """
        self._logger.debug(
            "Executing kexec on target ramdisk: args='%s'", boot_params
        )

        cmdline = boot_params.get('cmdline')
        kernel = boot_params.get('kernel_url')
        initrd = boot_params.get('initrd_url')

        # copy files to ramdisk
        guest.push_file(kernel, "/root/kernel")
        guest.push_file(initrd, "/root/initrd")

        session = guest.open_session()

        # execute kexec and ignore the return since it won't be
        # possible to read it
        session.run(
            "kexec kernel --initrd=initrd --command-line='{}'".format(
                cmdline
            ), ignore_ret=True
        )
    #_execute_kexec()

    def _setup_ramdisk_network(self, boot_params, lpar):
        """
        Auxiliary method. Setups the network on target ramdisk.
        This method is only used for the network boot method.

        Args:
            boot_params (dict): dictionary with boot parameters
            lpar (LogicalPartition): logical partition object

        Returns:
            None

        Raises:
            None
        """
        self._logger.debug(
            "Setting up ramdisk network: args='%s'", boot_params
        )


        mac_addr = boot_params.get('mac')
        ip_addr = boot_params.get('ip')
        subnet_addr = boot_params.get('mask')
        gw_addr = boot_params.get('gateway')
        channel = boot_params.get('device')

        ch_list = list()
        if channel.find(',') != -1:
            ch_list = channel.split(',')
        else:
            ch_list.append(channel)
            ch_list.append(hex(int(channel, 16)+1).strip("0x"))
            ch_list.append(hex(int(channel, 16)+2).strip("0x"))

        channels = ','.join(ch_list)

        # login into the system
        lpar.send_os_command(NETBOOT_USER)
        lpar.send_os_command(NETBOOT_PASSWORD)

        lpar.send_os_command("cio_ignore -r {}".format(channels))
        lpar.send_os_command(
            "znetconf -a {} -o portname=osaport".format(
                ch_list[0].replace("0.0.", ""))
        )
        lpar.send_os_command(
            "ifconfig enc{} hw ether {}".format(ch_list[0], mac_addr)
        )
        lpar.send_os_command(
            "ifconfig enc{} {} netmask {}".format(
                ch_list[0].replace("0.0.", ""), ip_addr, subnet_addr
            )
        )
        lpar.send_os_command("route add default gw {}".format(gw_addr))
    # _setup_ramdisk_network

    def _calculate_number_cpus(self, total_cpus, ifl_cpus):
        """
        Auxiliary method. If the number of IFL's are specified, it is necessary
        to calculate how many CP's need to be set following the equation:
            CP = Total - IFL

        Args:
            total_cpus (int): total number of cpus
            ifl_cpus (int): number of IFL cpus

        Returns:
            dict: number of cp's and ifl's

        Raises:
            None
        """
        args = dict()

        # If the number of IFL's are specified, we need to calculate how
        # many CP's are to be used.
        cp_cpus = total_cpus - ifl_cpus
        args['cp'] = cp_cpus
        args['ifl'] = ifl_cpus

        self._logger.debug("Number of cpus calculated: args='%s'", args)

        return args
    # _calculate_number_cpus()

    def _update_resources(self, args, image_profile):
        """
        Auxiliary method. If resources are different, we need to change the
        HMC profile before performing the LOAD, otherwise the amout of memory
        or cpus will not change.

        Args:
            args (dict): values to be applied to profile
            image_profile (ActivationProfile): ActivationProfile object that
                                               represents an image profile

        Returns:
            bool: true if resources were updated, false otherwise

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
            NotImplementedError: as it needs implementation
        """
        # TODO: implement feature when new fw enabling empty load-addr is
        # available
        self._logger.debug(
            "Method not implemented: args='%s','%s'", guest_name, parameters
        )

        raise NotImplementedError()
    # reboot()
# HypervisorHmc
