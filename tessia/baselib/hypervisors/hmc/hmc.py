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
from copy import deepcopy
from tessia.baselib.common.logger import get_logger
from tessia.baselib.guests.linux.linux import GuestLinux
from tessia.baselib.hypervisors.hmc.zhmc.zhmc import ZHmc
from tessia.baselib.hypervisors.base import HypervisorBase
from tessia.baselib.hypervisors.hmc.zhmc.exceptions import ZHmcError
from tessia.baselib.common.params_validators.utils import validate_params

import time
import subprocess

#
# CONSTANTS AND DEFINITIONS
#

# timeout in seconds before the netboot operation is considered failed
# TODO: compute the timeout based on the amount of storage memory (i.e. 1TB
# LPAR will take a long time to load)
NETBOOT_LOAD_TIMEOUT = 1800 # seconds

#
# CODE
#

class HypervisorHmc(HypervisorBase):
    """
    This class implements the driver to support the HMC hypervisor type
    """

    # the identifier for this hypervisor class
    HYP_ID = 'hmc'

    @validate_params
    def __init__(self, system_name, host_name, user, passwd, parameters):
        """
        Constructor, store instance values via base class and initialize logger

        Args:
            system_name (str): the name of the CPC hosting the target LPAR
            host_name (str): hostname or ip address of system
            user (str): user to login to HMC
            passwd (str): password to login to HMC
            parameters (dict): values specific to each hypervisor type

        Raises:
            None
        """
        # base class will store instances values
        super().__init__(
            # in hmc classic mode the names are always uppercased, therefore we
            # make sure we use it as so
            system_name.upper(),
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

        cpc = self._session.get_cpc(self.name)
        guest_name = guest_name.upper()
        lpar = cpc.get_lpar(guest_name)
        # Profiles have the same name as the LPAR's
        image_profile = cpc.get_image_profile(guest_name)

        # Calculating the number of processors chosen
        args = self._calculate_number_cpus(cpu,
                                           parameters.get('cpus_cp', 0),
                                           parameters.get('cpus_ifl', 0),
                                           cpc.get_cpus())
        # Set storage
        args['mem'] = memory

        try:
            # update the profile parameters if necessary
            update = self._update_resources(args, image_profile)

            # image profile updated: we need to activate the LPAR again so
            # changes can take effect
            if update or lpar.status == 'not-activated':
                lpar.activate()

            self._load(lpar, parameters['boot_params'])
        except Exception as exc:
            self._logger.debug(
                'An error ocurred during start, info:', exc_info=True)
            raise ZHmcError('Operation failed with: {}'.format(str(exc)))
    # start()

    def _execute_kexec(self, guest, kernel_url, initrd_url, cmdline):
        """
        Auxiliary method. Execute kexec command on target host.
        This method is only used for the network boot method.

        Args:
            guest (GuestLinux): guest linux object
            kernel_url (string): url to kernel
            initrd_url (string): url to initrd image
            cmdline (string): kernel cmdline

        Raises:
            None
        """
        self._logger.debug(
            "Executing kexec: guest='%s' kernel_url='%s' initrd_url='%s' "
            "cmdline='%s'", guest, kernel_url, initrd_url, cmdline
        )

        # copy files to ramdisk
        guest.push_file(kernel_url, "/tmp/kernel")
        if initrd_url:
            guest.push_file(initrd_url, "/tmp/initrd")

        session = guest.open_session()

        # Execute kexec and ignore the return since it won't be possible to
        # read it. Also use nohup to prevent a race condition where the ssh
        # connection dies too fast before the command is processed.
        kexec_cmd = 'nohup kexec /tmp/kernel'
        if initrd_url:
            kexec_cmd += ' --initrd=/tmp/initrd'
        if cmdline:
            kexec_cmd += " --command-line='{}'".format(cmdline)
        kexec_cmd += ' &>/tmp/kexec.log'
        session.run(
            "killall -9 sshd; {}".format(kexec_cmd), ignore_ret=True)
        time.sleep(1)
    #_execute_kexec()

    def _load(self, lpar, boot_params):
        """
        Perform the load operation on a profile according to the specified
        method.

        Args:
            lpar (LogicalPartition): profile instance
            boot_params (dict): options as specified in json schema

        Raises:
            ValueError: if an unsupported boot method is specified
            RuntimeError: for netboot method, in case of load timeout or no aux
                disk configured
        """
        # perform load of a SCSI disk
        if boot_params['boot_method'] == 'scsi':
            lpar.scsi_load(
                boot_params['zfcp_devicenr'],
                boot_params['wwpn'],
                boot_params['lun'],
            )
        # perform load of a DASD disk
        elif boot_params['boot_method'] == 'dasd':
            lpar.load(boot_params['devicenr'])
        else:
            raise ValueError('Unsupported boot method {}'
                             .format(boot_params['boot_method']))

        net_setup = boot_params.get('netsetup', {})
        net_boot = boot_params.get('netboot')
        # no network setup requested: nothing else to do
        if not net_setup:
            return

        # make sure lpar is up before trying to execute commands
        timeout = time.time() + NETBOOT_LOAD_TIMEOUT
        while lpar.get_properties()['status'] != 'operating':
            if time.time() >= timeout:
                raise RuntimeError(
                    "Timed out while waiting for load of operating system"
                )
            time.sleep(1)

        # password cannot be optional as GuestLinux would fail to connect to a
        # system without password
        os_passwd = net_setup['password']
        # enable network on loaded operating system
        self._setup_network(net_setup, lpar, os_passwd)

        # network is up; open a ssh session to the system
        guest = GuestLinux(lpar.name, net_setup['ip'], 'root', os_passwd, {})
        guest.login()

        # netboot config url provided: perform a kexec to simulate netboot
        if net_boot:
            kernel_url = net_boot['kernel_url']
            initrd_url = net_boot.get('initrd_url')
            cmdline = net_boot.get('cmdline')
            self._execute_kexec(guest, kernel_url, initrd_url, cmdline)

        guest.logoff()
    # _load()

    def _setup_network(self, net_setup, lpar, os_passwd):
        """
        Auxiliary method. Setup the network on the loaded operating system.

        Args:
            net_setup (dict): dictionary with network parameters
            lpar (LogicalPartition): logical partition object
            os_passwd (string): operating system root password

        Raises:
            RuntimeError: in case of timeout while waiting for network to come
                          up
        """
        self._logger.debug(
            "Setting up network: args='%s'", net_setup
        )

        net_cmds = []
        ip_addr = net_setup['ip']
        dns_servers = net_setup.get('dns')
        subnet_addr = net_setup['mask']
        gw_addr = net_setup['gateway']

        # PCI card: find out interface name
        if net_setup.get('type') == 'pci':
            # export interface name
            net_cmds.extend([
                "DEV_PATH=$(dirname $(grep -m1 -r '0x0*{}' --include "
                "function_id /sys/bus/pci/devices/*))".format(
                    net_setup['device'].lower()),
                "export IFACE_NAME=$(ls -1 ${DEV_PATH}/net | head -1)",
            ])

        # OSA card: define additional options
        else:
            mac_addr = net_setup['mac']
            channel = net_setup['device']
            options = deepcopy(net_setup.get('options', {}))
            try:
                layer2 = options.pop('layer2')
                layer2 = {
                    'true': 1, 'false': 0, '1': 1, '0': 0
                }[str(layer2).lower()]
            # option not specified or unknown value used: defaults to off
            except (KeyError, ValueError):
                layer2 = 0

            if channel.find(',') != -1:
                ch_list = channel.split(',')
            else:
                ch_list = [channel]
                ch_list.append(hex(int(channel, 16)+1).lstrip("0x"))
                ch_list.append(hex(int(channel, 16)+2).lstrip("0x"))

            # build the options string, layer2 should always come first
            str_option = '-o layer2={}'.format(layer2)
            for key, value in options.items():
                str_option += ' -o {}={}'.format(key, value)

            net_cmds.extend([
                # make the osa channels available
                "cio_ignore -r {}".format(','.join(ch_list)),
                # activate the osa card
                "znetconf -a {} {}".format(
                    ch_list[0].replace("0.0.", ""), str_option),
            ])

            # set interface name
            full_ccw = ch_list[0]
            if '.' not in full_ccw:
                full_ccw = '0.0.{}'.format(full_ccw)
            net_cmds.append('export IFACE_NAME=$(ls -1 /sys/devices/qeth/{}/'
                            'net | head -1)'.format(full_ccw))
            # layer2 active: set mac address for network interface
            if layer2 == 1 and mac_addr:
                net_cmds.append(
                    "ifconfig $IFACE_NAME hw ether {}".format(mac_addr))

        net_cmds.extend([
            # set ip address and network mask
            "ifconfig $IFACE_NAME {} netmask {}".format(
                ip_addr, subnet_addr),
            # set default gateway
            "route add default gw {}".format(gw_addr),
        ])
        if dns_servers:
            net_cmds.append("echo > /etc/resolv.conf")
            for dns_entry in dns_servers:
                net_cmds.append(
                    "echo 'nameserver {}' >> /etc/resolv.conf"
                    .format(dns_entry))
        timeout = time.time() + NETBOOT_LOAD_TIMEOUT
        while True:
            # the api has a limit of 200 chars per call so we need to split the
            # commands in smaller pieces
            lpar.send_os_command('root')
            lpar.send_os_command(os_passwd)
            for cmd in net_cmds:
                str_buf = ''
                for char in cmd:
                    str_buf += char
                    if len(str_buf) == 100:
                        str_buf += '\\'
                        lpar.send_os_command(str_buf)
                        str_buf = ''
                lpar.send_os_command('{} && '.format(str_buf))
            # sometimes the LPAR is unreachable from the network until a ping
            # is performed (likely because of arp cache)
            lpar.send_os_command("true; ping -c 1 {}".format(gw_addr))
            # verify if system is reachable
            try:
                subprocess.run(
                    'ping -c 1 -w 5 ' + ip_addr, shell=True, check=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                pass
            # network is up: commands succeeded
            else:
                break

            if time.time() >= timeout:
                raise RuntimeError(
                    "Timed out while waiting for network on loaded operating "
                    "system")
            time.sleep(5)

    # _setup_network()

    def _calculate_number_cpus(self, cpus_gen, cpus_cp, cpus_ifl, cpc_avail):
        """
        Auxiliary method, determines the number of CPs and IFLs for activation
        based on requested parameters. There are two strategies to handle
        the call:

        Dynamic: no cpu type is defined (cpus_cp and cpus_ifl are zero), in
        this case the function allocates 'cpus_gen' number of CPUs first
        allocating IFLs, then CPs, according to the CPC availability.

        Static: cpu types are defined exactly, in this case the function only
        validates that the CPC resources can fulfill the requested numbers.

        Args:
            cpus_gen (int): requested number of 'generic' cpus (dynamic
                            approach)
            cpus_cp (int): requested number of general purpose cpus
                           (static approach)
            cpus_ifl (int): requested number of IFL cpus (static approach)
            cpc_avail (dict): contains CPC availability of IFLs and CPs

        Returns:
            dict: number of CPs and IFLs to be used for activation

        Raises:
            RuntimeError: in case the available CPUs in the CPC cannot meet
                          the requested CPU numbers
        """
        ret_args = dict()

        # no cpu type specified: use dynamic strategy
        if cpus_cp == 0 and cpus_ifl == 0:
            # total number of cpus exceeds cpc availability: report error
            if cpus_gen > (cpc_avail['cpus_ifl'] + cpc_avail['cpus_cp']):
                raise RuntimeError(
                    'Not enough CPUs available in CPC. Requested: {} CPUs. '
                    'Available: {} CPs, {} IFLs.'.format(
                        cpus_gen, cpc_avail['cpus_cp'], cpc_avail['cpus_ifl']))

            if cpus_gen < cpc_avail['cpus_ifl']:
                ret_args['ifl'] = cpus_gen
                ret_args['cp'] = 0
            else:
                ret_args['ifl'] = cpc_avail['cpus_ifl']
                ret_args['cp'] = cpus_gen - ret_args['ifl']
        # a cpu type was specified: use static strategy
        else:
            if (cpus_cp > cpc_avail['cpus_cp'] or
                    cpus_ifl > cpc_avail['cpus_ifl']):
                raise RuntimeError(
                    'Not enough CPUs available in CPC. Requested: {} CPs, {} '
                    'IFLs. Available: {} CPs, {} IFLs.'.format(
                        cpus_cp, cpus_ifl, cpc_avail['cpus_cp'],
                        cpc_avail['cpus_ifl']))

            ret_args['cp'] = cpus_cp
            ret_args['ifl'] = cpus_ifl
        self._logger.debug("Number of cpus calculated: %s", ret_args)

        return ret_args
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
                               In this case not used.

        Raises:
            ZHmcError: if session is not created
        """

        if self._session is None:
            raise ZHmcError("You need to login first")

        self._logger.debug(
            "performing STOP HypervisorHMC: name='%s' host_name='%s' "
            "user='%s' guest_name=%s parameters='%s'",
            self.name,
            self.host_name,
            self.user,
            guest_name,
            str(self.parameters)
        )
        cpc = self._session.get_cpc(self.name)
        lpar = cpc.get_lpar(guest_name.upper())

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
