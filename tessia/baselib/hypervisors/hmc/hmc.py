# Copyright 2016, 2017, 2019 IBM Corp.
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
from requests.packages import urllib3  # pylint: disable=import-error
from tessia.baselib.common.logger import get_logger
from tessia.baselib.guests.linux.linux import GuestLinux
from tessia.baselib.hypervisors.base import HypervisorBase
from tessia.baselib.hypervisors.hmc.messages import Messages
from tessia.baselib.common.params_validators.utils import validate_params
from urllib.parse import urlsplit

import time
import zhmcclient

#
# CONSTANTS AND DEFINITIONS
#

# string to wait for in operating system messages
MESSAGES_DEFAULT_PATTERN = 'debirf-rescue:~#'
# how long to load messages after live image is booted into installer
MSG_POST_LOAD_DURATION = 90  # seconds
# timeout in seconds for network to be up
NETBOOT_LOAD_TIMEOUT = 300  # seconds
# timeout in seconds before the partition is operating
OS_MESSAGES_TIMEOUT = 600  # seconds
# list of manageable DPM partition statuses
VALID_DPM_STATUSES = ('active', 'paused', 'terminated', 'stopped')
# command used to download kernel and initrd
WGET_CMD = "wget --no-check-certificate -nv -O '{tgt}' '{src}'"

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
            # CPC names are always uppercased
            system_name.upper(),
            host_name,
            user,
            passwd,
            parameters
        )

        # HMC session and client objects to be initialized by login()
        self._conn = None
        # suppress warnings from urllib3 related to cert validation
        urllib3.disable_warnings(
            category=urllib3.exceptions.InsecureRequestWarning)

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

    @staticmethod
    def _assert_dpm_status(status):
        """
        Validate that the DPM partition is in a manageable status
        """
        if status not in VALID_DPM_STATUSES:
            raise RuntimeError(
                "Partition cannot be managed because its current status "
                "<{}> is invalid, valid statuses are: {}"
                .format(status, ','.join(VALID_DPM_STATUSES)))
    # _assert_dpm_status()

    def _compute_cpus(self, cpus_gen, cpus_cp, cpus_ifl, cpc_avail):
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
    # _compute_cpus()

    def _do_netsetup(self, guest_obj, boot_params, notify_boot=None):
        """
        Perform the steps required to bring up the network on the Linux system
        """
        net_setup = boot_params.get('netsetup')
        # no network setup requested: nothing to do
        if not net_setup:
            return

        # password cannot be optional as GuestLinux would fail to connect to a
        # system without password
        os_passwd = net_setup['password']
        # enable network on loaded operating system
        net_cmds = self._prepare_setup_network_cmds(net_setup)

        self._logger.debug("Opening OS messages channel")
        os_channel_topic = guest_obj.open_os_message_channel(
            include_refresh_messages=True)

        with Messages.connect(os_channel_topic, self.host_name,
                              self.user, self.passwd) as receiver:
            self._logger.debug("Waiting for live image login prompt")
            self._send_commands(
                guest_obj,
                [('debirf-rescue login:', 'root'), ('Password:', os_passwd)],
                receiver)

            self._logger.debug("Setting up network on live image")
            self._send_commands(guest_obj, net_cmds, receiver)

            net_boot = boot_params.get('netboot')
            if net_boot:
                self._logger.debug("Performing netboot")
                self._execute_kexec(guest_obj, receiver,
                                    net_setup, net_boot)

                # check if we have a notification event in parameters
                if notify_boot:
                    self._logger.debug("Notify initial boot complete")
                    notify_boot.set()
                # wait a little to collect reboot logs
                timeout = time.time() + MSG_POST_LOAD_DURATION
                while timeout - time.time() > 0:
                    for msg in receiver.get_messages(
                            timeout=max(1.0, min(MSG_POST_LOAD_DURATION,
                                                 timeout-time.time()))):
                        self._logger.debug('OS message: %s', msg)

        self._logger.debug("Live image stage finished")
    # _do_netsetup()

    def _execute_kexec(self, guest_obj, receiver, net_setup, net_boot):
        """
        Auxiliary method. Execute kexec command on target host.
        This method is only used for the network boot method.

        Args:
            guest_obj (Lpar or Partition): zhmcclient object
            receiver (Messages): messages interface
            net_setup (dict): net_setup parameters
            net_boot (dict): net_boot parameters

        Raises:
            RuntimeError: cannot upload a file via linux session
        """

        kernel_url = net_boot['kernel_url']
        initrd_url = net_boot.get('initrd_url')
        cmdline = net_boot.get('cmdline')

        # send an empty string first to get a matching pattern in send_commands
        kexec_cmds = [('', ' ')]

        for source, target in [(kernel_url, '/tmp/kernel'),
                               (initrd_url, '/tmp/initrd')]:
            if source and urlsplit(source).scheme not in (
                    'http', 'https', 'ftp'):
                # connect with an SSH client and transfer files
                self._logger.debug("Transferring %s with SSH client", source)
                linux_obj = GuestLinux(
                    guest_obj.name, net_setup['ip'],
                    'root', net_setup['password'], {})
                try:
                    linux_obj.login()
                    linux_obj.push_file(source, target)
                    linux_obj.logoff()
                except Exception as exc:
                    raise RuntimeError(
                        "Failed to upload {}".format(source)) from exc
            elif source:
                kexec_cmds.append(WGET_CMD.format(src=source, tgt=target))

        kexec_cmd = 'kexec /tmp/kernel'
        if initrd_url:
            kexec_cmd += ' --initrd=/tmp/initrd'
        if cmdline:
            kexec_cmd += " --command-line='{}'".format(cmdline)

        kexec_cmds.append(kexec_cmd)

        self._logger.debug(
            "Executing kexec: kernel_url='%s' initrd_url='%s' cmd='%s'",
            kernel_url, initrd_url, kexec_cmd
        )
        self._send_commands(guest_obj, kexec_cmds, receiver)

        time.sleep(1)
    # _execute_kexec()

    def _get_cpc(self, cpc_name):
        """
        Return the CPC object which corresponds to the name provided.
        """
        try:
            cpc = self._conn[0].cpcs.find(name=cpc_name)
        except zhmcclient.NotFound:
            raise ValueError(
                'CPC <{}> does not exist or is not accessible by this HMC user'
                .format(self.name)) from None
        return cpc
    # _get_cpc()

    def _get_guest(self, cpc_obj, guest_name):
        """
        Return the Partition (if on DPM) or Lpar (non DPM) object which
        corresponds to the name provided.
        """
        if cpc_obj.dpm_enabled:
            try:
                guest_obj = cpc_obj.partitions.find(name=guest_name.lower())
            except zhmcclient.NotFound:
                raise ValueError(
                    'Partition <{}> does not exist or is not accessible by '
                    'this HMC user'.format(guest_name.lower())) from None
            self._assert_dpm_status(guest_obj.get_property('status'))
        else:
            try:
                guest_obj = cpc_obj.lpars.find(name=guest_name.upper())
            except zhmcclient.NotFound:
                raise ValueError(
                    'LPAR <{}> does not exist or is not accessible by '
                    'this HMC user'.format(guest_name.upper())) from None
        return guest_obj
    # _get_guest()

    def _get_svol_uri(self, part_obj, boot_params):
        """
        Find the uri of a storage volume
        """
        if boot_params['boot_method'] == 'scsi':
            sg_type = 'fcp'
            prop_key = 'uuid'
            prop_value = boot_params['uuid']
        else:
            sg_type = 'fc'
            prop_key = 'device-number'
            prop_value = boot_params['devicenr']

        self._logger.debug("Looking for storage volume object with %s='%s'",
                           prop_key, prop_value)
        # search the corresponding volume in the storage groups attached to the
        # partition
        for sg_uri in part_obj.get_property('storage-group-uris'):
            sg_obj = (part_obj.manager.cpc.manager.console.storage_groups
                      .resource_object(sg_uri))
            if sg_obj.get_property('type').lower() != sg_type:
                self._logger.debug(
                    "Skipping storage group %s, type '%s' (actual) != '%s' "
                    "(expected)", sg_obj.get_property('name'),
                    sg_obj.get_property('type').lower(), sg_type)
                continue
            # find the matching volume
            for sg_vol in sg_obj.storage_volumes.list():
                sg_vol.pull_full_properties()
                try:
                    sg_vol_value = sg_vol.properties[prop_key]
                except KeyError:
                    continue
                if sg_vol_value.lower() != prop_value.lower():
                    continue
                if sg_vol.properties['usage'] != 'boot':
                    sg_vol.update_properties({'usage': 'boot'})
                return sg_vol.get_property('element-uri')

        raise ValueError(
            'Storage volume <{}:{}> not found or not attached to partition'
            .format(prop_key, prop_value))
    # _get_svol_uri()

    def _load(self, guest_obj, boot_params):
        """
        Perform the load operation on a profile according to the specified
        method.

        Args:
            guest_obj (Lpar or Partition): zhmcclient object
            boot_params (dict): options as specified in json schema

        Raises:
            NotImplementedError: if cpc in dpm mode has no storage management
                                 firmware feature
            ValueError: if an unsupported boot method is specified
        """
        # dpm mode
        if isinstance(guest_obj, zhmcclient.Partition):
            # perform load of a storage volume
            if boot_params['boot_method'] in ('dasd', 'scsi'):
                # make sure storage management is available
                try:
                    guest_obj.feature_enabled('dpm-storage-management')
                except ValueError:
                    raise NotImplementedError(
                        'Load operation on DPM enabled CPCs without storage '
                        'management firmware feature is not supported')

                svol_uri = self._get_svol_uri(guest_obj, boot_params)
                # update_boot_params
                update_props = {
                    'boot-device': 'storage-volume',
                    'boot-storage-volume': svol_uri,
                }
                if guest_obj.get_property('status') != 'stopped':
                    guest_obj.stop(wait_for_completion=True)
                    guest_obj.wait_for_status('stopped')
                guest_obj.update_properties(update_props)
                guest_obj.start(wait_for_completion=True)
            # network boot
            elif boot_params['boot_method'] in ('ftp', 'ftps', 'sftp'):
                # update_boot_params
                parsed_url = urlsplit('{boot_method}://{insfile}'.format(
                    **boot_params))
                update_props = {
                    'boot-device': boot_params['boot_method'],
                    'boot-ftp-host': parsed_url.hostname,
                    'boot-ftp-username': parsed_url.username or 'anonymous',
                    'boot-ftp-password': parsed_url.password or 'anonymous',
                    'boot-ftp-insfile': parsed_url.path,
                }
                if guest_obj.get_property('status') != 'stopped':
                    guest_obj.stop(wait_for_completion=True)
                    guest_obj.wait_for_status('stopped')
                guest_obj.update_properties(update_props)
                guest_obj.start(wait_for_completion=True)
            return

        # perform load of a SCSI disk
        if boot_params['boot_method'] == 'scsi':
            guest_obj.scsi_load(
                load_address=self._normalize_address(boot_params['devicenr']),
                wwpn=boot_params['wwpn'],
                lun=boot_params['lun'],
                wait_for_completion=True,
                force=True
            )
        # perform load of a DASD disk
        elif boot_params['boot_method'] == 'dasd':
            guest_obj.load(
                load_address=self._normalize_address(boot_params['devicenr']),
                wait_for_completion=True,
                force=True)
        # sanity check
        elif boot_params['boot_method'] in ('ftp', 'ftps', 'sftp'):
            raise ValueError('{} boot is only available in DPM mode'.format(
                boot_params['boot_method']))
    # _load()

    @staticmethod
    def _normalize_address(address):
        """
        Convert the load address to the format expected by the HMC API.

        Args:
            address (str): string in the format 0.0.1500 or 1500

        Returns:
            str: normalized load address
        """
        return address.replace('.', '')[-5:]
    # _normalize_address()

    def _prepare_setup_network_cmds(self, net_setup):
        """
        Auxiliary method. Setup the network on the loaded operating system.

        Args:
            net_setup (dict): dictionary with network parameters

        Returns:
            List[str]: network setup commands
        """
        self._logger.debug(
            "Setting up network: args='%s'",
            # log arguments without a specific key
            {k: v for k, v in net_setup.items() if k != 'password'}
        )

        net_cmds = []
        ip_addr = net_setup['ip']
        dns_servers = net_setup.get('dns')
        subnet_mask = net_setup['mask']
        gw_addr = net_setup['gateway']
        vlan_id = net_setup.get('vlan')

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
                    "ip link set $IFACE_NAME address {}".format(mac_addr))

        if vlan_id:
            net_cmds.extend([
                'ip link add link ${{IFACE_NAME}} name ${{IFACE_NAME}}.{vlan} '
                'type vlan id {vlan}'.format(vlan=vlan_id),
                'ip link set $IFACE_NAME up',
                'export IFACE_NAME=${{IFACE_NAME}}.{}'.format(vlan_id)
            ])
        net_cmds.extend([
            # set ip address and network mask
            "ip addr add {}/{} dev $IFACE_NAME".format(ip_addr, subnet_mask),
            "ip link set $IFACE_NAME up",
            # set default gateway
            "ip route add default via {}".format(gw_addr),
        ])
        if dns_servers:
            net_cmds.append("echo > /etc/resolv.conf")
            for dns_entry in dns_servers:
                net_cmds.append(
                    "echo 'nameserver {}' >> /etc/resolv.conf"
                    .format(dns_entry))

        # sometimes the LPAR is unreachable from the network until a ping
        # is performed (likely because of arp cache)
        net_cmds.append("ping -c 1 {}".format(gw_addr))
        return net_cmds
    # _prepare_setup_network_cmds()

    def _send_commands(self, guest_obj, commands, msg_channel):
        """
        Send command list to a system via HMC

        Args:
            guest_obj (Lpar or Partition): zhmcclient object
            commands (List): list of commands to send.
                             Command may be a tuple (pattern, command) to wait
                             for a pattern to appear on msg_channel
            msg_channel (zhmcclient.NotificationReceiver): message channel

        Raises:
            TimeoutError: operation took too long
        """
        if not commands:
            return

        # command generator
        def _get_cmd(commands):
            for cmd in commands:
                if isinstance(cmd, str):
                    yield (MESSAGES_DEFAULT_PATTERN, cmd)
                else:
                    yield cmd

        # the api has a limit of 200 chars per call so we need
        # to split the commands in smaller pieces
        def _string_to_chunks(string, size=180):
            for start in range(0, len(string), size):
                yield string[start:start+size] + (
                    '\\' if start+size < len(string) else '')

        timeout = time.time() + OS_MESSAGES_TIMEOUT
        command_gen = _get_cmd(commands)
        pattern, cmd = next(command_gen)
        try:
            # allow first command to skip waiting for messages
            # by specifying an empty wait pattern
            if not pattern:
                for chunk in _string_to_chunks(cmd):
                    guest_obj.send_os_command(chunk)
                pattern, cmd = next(command_gen)

            while time.time() < timeout:
                # wait for pattern to appear
                messages = msg_channel.get_messages(60.0)
                if not messages:
                    self._logger.debug("Still waiting for '%s' prompt",
                                       pattern)
                    continue

                for msg in messages:
                    self._logger.debug("OS message: %s", msg)
                    if pattern in msg:
                        for chunk in _string_to_chunks(cmd):
                            guest_obj.send_os_command(chunk)
                        pattern, cmd = next(command_gen)

        except StopIteration:
            pass

        if time.time() > timeout:
            raise TimeoutError(
                "Timed out communicating with OS Messages interface")
    # _send_commands()

    def _update_resources_lpar(self, args, guest_obj):
        """
        Auxiliary method. If resources are different, we need to change the
        HMC profile before performing the LOAD, otherwise the amount of memory
        or cpus will not change.

        Args:
            args (dict): values to be applied to profile
            guest_obj (Lpar): zhmclient Lpar object
        """
        # profiles have the same name as the LPARs
        image_profile = guest_obj.manager.cpc.image_activation_profiles.find(
            name=guest_obj.properties['name'])
        image_profile.pull_full_properties()
        img_properties = image_profile.properties
        updates = dict()

        # set memory specified by user in profile
        if 'mem' in args and img_properties['central-storage'] != args['mem']:
            updates['central-storage'] = args['mem']

        if 'cp' in args and (
                img_properties['number-shared-general-purpose-processors'] !=
                args['cp']):
            updates['number-shared-general-purpose-processors'] = args['cp']

        if 'ifl' in args and (
                img_properties['number-shared-ifl-processors'] != args['ifl']):
            updates['number-shared-ifl-processors'] = args['ifl']

        if img_properties['processor-usage'] != 'shared':
            updates['processor-usage'] = 'shared'

        # new config matches profile: nothing to do
        if not updates:
            return

        self._logger.debug("Updating image profile: args='%s'", updates)
        image_profile.update_properties(updates)
        # we need to activate the LPAR or re-activate so changes get applied
        guest_obj.activate(activation_profile_name=img_properties['name'],
                           wait_for_completion=True, force=True)
    # _update_resources_lpar()

    def _update_resources_partition(self, args, part_obj):
        """
        Update the partition properties to the resquested memory and cpu values

        Args:
            part_obj (Partition): zhmclient Partition object
            args (dict): values to be applied
        """
        part_obj.pull_full_properties()
        properties = part_obj.properties
        updates = dict()

        if 'mem' in args and properties['maximum-memory'] != args['mem']:
            updates['initial-memory'] = args['mem']
            updates['maximum-memory'] = args['mem']

        if 'cp' in args and properties['cp-processors'] != args['cp']:
            updates['cp-processors'] = args['cp']

        if 'ifl' in args and properties['ifl-processors'] != args['ifl']:
            updates['ifl-processors'] = args['ifl']

        if properties['processor-mode'] != 'shared':
            updates['processor-mode'] = 'shared'

        # new config matches partition profile: nothing to do
        if not updates:
            return

        self._logger.debug(
            "Updating partition properties: args='%s'", updates
        )
        # do not perform a stop on a stopped partition as this will raise an
        # error
        if part_obj.get_property('status') != 'stopped':
            part_obj.stop(wait_for_completion=True)
            part_obj.wait_for_status('stopped')
            # the object has caching issues which in certain situations cause
            # the status not to be updated, so we explicitly fetch properties
            # again here
            part_obj.pull_full_properties()
        part_obj.update_properties(updates)
    # _update_resources_partition()

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
            "user='%s' parameters='%s' timeout='%s'",
            self.name,
            self.host_name,
            self.user,
            str(self.parameters),
            timeout,
        )

        if self._conn is not None:
            self._logger.warning(
                "Login called with connection already active:"
                " dropping previous connection object"
            )

        rt_config = zhmcclient.RetryTimeoutConfig(connect_timeout=timeout)
        session = zhmcclient.Session(
            self.host_name, self.user, self.passwd,
            retry_timeout_config=rt_config,
            port=self.parameters.get('port', zhmcclient.DEFAULT_HMC_PORT))
        session.logon()
        self._conn = (zhmcclient.Client(session), session)
    # login()

    def logoff(self):
        """
        Close an active connection to the HMC

        Args:
            None

        Raises:
            ConnectionError: if session does not exist yet
        """
        self._logger.debug(
            "performing LOGOFF HypervisorHMC: name='%s' host_name='%s' "
            "user='%s' parameters='%s'",
            self.name,
            self.host_name,
            self.user,
            str(self.parameters)
        )
        if self._conn is None:
            raise ConnectionError("You need to login first.")

        self._conn[1].logoff()
        self._conn = None
    # logoff()

    @validate_params
    def start(self, guest_name, cpu, memory, parameters, notify=None):
        """
        Activate (If necessary) and IPL a target LPAR

        Args:
            guest_name (str): LPAR/partition name
            cpu (int): number of CPU's to assign
            memory (int): amount of memory to assign in megabytes.
            parameters (dict): contains the CPC name and boot type config
            notify (Event):    A notification object

        Raises:
            ConnectionError: if session does not exist yet
            ValueError: if an object (cpc, lpar) cannot be retrieved
            zhmcclient.HTTPError: an HMC operation fails
        """
        self._logger.debug(
            "performing START HypervisorHMC: name='%s' host_name='%s' "
            "user='%s' guest_name='%s' cpu='%s' memory='%s' parameters='%s'",
            self.name,
            self.host_name,
            self.user,
            guest_name,
            cpu,
            memory,
            str(parameters)
        )

        if not self._conn:
            raise ConnectionError("You need to login first")

        cpc_obj = self._get_cpc(self.name)
        # validate load parameters against cpc operation mode
        if parameters['boot_params']['boot_method'] == 'scsi':
            if cpc_obj.dpm_enabled and (
                    'uuid' not in parameters['boot_params']):
                raise ValueError(
                    'For a CPC in DPM mode the scsi volume UUID must be '
                    'provided')
            if not cpc_obj.dpm_enabled and not(
                    parameters['boot_params'].get('lun') and
                    parameters['boot_params'].get('wwpn') and
                    parameters['boot_params'].get('devicenr')):
                raise ValueError('For a CPC in classic mode the scsi DEVNO, '
                                 'WWPN and LUN must be provided')
        # validate cpus input
        if cpu and (parameters.get('cpus_cp') or parameters.get('cpus_ifl')):
            raise ValueError(
                'cpu parameter must be 0 when static configuration (cpus_cp '
                'and/or cpus_ifl) is entered')

        guest_obj = self._get_guest(cpc_obj, guest_name)

        resource_args = {}
        # cpu specified: compute number of processors
        if cpu or parameters.get('cpus_cp') or parameters.get('cpus_ifl'):
            resource_args = self._compute_cpus(
                cpu, parameters.get('cpus_cp', 0),
                parameters.get('cpus_ifl', 0),
                {'cpus_ifl': cpc_obj.properties['processor-count-ifl'],
                 'cpus_cp': (
                     cpc_obj.properties['processor-count-general-purpose'])}
            )
        # set storage (0 means do not update the parameter)
        if memory:
            resource_args['mem'] = memory

        # resources specified by user: update guest's properties as needed
        if resource_args:
            if isinstance(guest_obj, zhmcclient.Partition):
                self._update_resources_partition(resource_args, guest_obj)
            else:
                self._update_resources_lpar(resource_args, guest_obj)

        # classic mode: make sure the LPAR is active before performing a load
        if isinstance(guest_obj, zhmcclient.Lpar) and (
                guest_obj.get_property('status') == 'not-activated'):
            self._logger.info("Activating LPAR")
            try:
                guest_obj.activate(
                    activation_profile_name=guest_obj.properties['name'],
                    wait_for_completion=True, force=True)
            except zhmcclient.HTTPError as exc:
                if exc.http_status == 500 and exc.reason == 263:
                    # Activation is complete. The load was not processed.
                    self._logger.info("LPAR activation is complete")
                else:
                    raise

        self._load(guest_obj, parameters['boot_params'])
        self._do_netsetup(guest_obj, parameters['boot_params'], notify)
    # start()

    @validate_params
    def stop(self, guest_name, parameters):
        """
        Deactivate a target LPAR

        Args:
            guest_name (str): target LPAR name.
            parameters (dict): content specific to each hypervisor type.
                               In this case not used.

        Raises:
            ConnectionError: if session is not created yet
        """
        if self._conn is None:
            raise ConnectionError("You need to login first")

        self._logger.debug(
            "performing STOP HypervisorHMC: name='%s' host_name='%s' "
            "user='%s' guest_name=%s parameters='%s'",
            self.name,
            self.host_name,
            self.user,
            guest_name,
            str(parameters)
        )
        cpc_obj = self._get_cpc(self.name)
        guest_obj = self._get_guest(cpc_obj, guest_name)

        if isinstance(guest_obj, zhmcclient.Partition):
            # partition already stopped: nothing to do
            if guest_obj.get_property('status') == 'stopped':
                return
            guest_obj.stop(wait_for_completion=True)
        else:
            guest_obj.deactivate(wait_for_completion=True, force=True)
    # stop()

    def reboot(self, guest_name, parameters):
        """
        Reboot a target LPAR

        Args:
            guest_name (str): target LPAR name.
            parameters (dict): content specific to each hypervisor type.
            In this case, the CPC name.

        Raises:
            ConnectionError: if session is not created yet
            zhmcclient.HTTPError: an HMC operation fails
        """
        if self._conn is None:
            raise ConnectionError("You need to login first")

        self._logger.debug(
            "performing REBOOT HypervisorHMC: name='%s' host_name='%s' "
            "user='%s' guest_name=%s parameters='%s'",
            self.name,
            self.host_name,
            self.user,
            guest_name,
            str(parameters)
        )
        cpc_obj = self._get_cpc(self.name)
        guest_obj = self._get_guest(cpc_obj, guest_name)

        # dpm mode: simply stop and start
        if isinstance(guest_obj, zhmcclient.Partition):
            if guest_obj.get_property('status') != 'stopped':
                guest_obj.stop(wait_for_completion=True)
                guest_obj.wait_for_status('stopped')
            guest_obj.start(wait_for_completion=True)
            return

        # classic mode: need to retireve last used load address and load type,
        # then deactivate/activate/load
        guest_obj.pull_full_properties()
        img_profile = guest_obj.properties['next-activation-profile-name']
        # lun set: use scsi load
        if guest_obj.properties['last-used-logical-unit-number'] != '0':
            load_method = guest_obj.scsi_load
            load_kwargs = {
                'load_address': guest_obj.properties['last-used-load-address'],
                'wwpn': guest_obj.properties['last-used-world-wide-port-name'],
                'lun': guest_obj.properties['last-used-logical-unit-number'],
                'wait_for_completion': True,
                'force': True,
            }
        # normal load
        else:
            load_method = guest_obj.load
            load_kwargs = {
                'load_address': guest_obj.properties['last-used-load-address'],
                'wait_for_completion': True,
                'force': True,
            }
        guest_obj.deactivate(wait_for_completion=True, force=True)
        self._logger.info("Activating LPAR")
        try:
            guest_obj.activate(
                activation_profile_name=img_profile,
                wait_for_completion=True, force=True)
        except zhmcclient.HTTPError as exc:
            if exc.http_status == 500 and exc.reason == 263:
                # Activation is complete. The load was not processed.
                self._logger.info("LPAR activation is complete")
            else:
                raise

        load_method(**load_kwargs)
    # reboot()
# HypervisorHmc
