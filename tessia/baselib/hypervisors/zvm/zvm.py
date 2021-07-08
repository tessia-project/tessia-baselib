# Copyright 2016, 2017, 2018 IBM Corp.
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
Implementation of hypervisor interface for Zvm
"""

#
# IMPORTS
#
from tempfile import NamedTemporaryFile
from tessia.baselib.common.logger import get_logger
from tessia.baselib.common.params_validators.utils import validate_params
from tessia.baselib.guests.cms.cms import GuestCms, ERROR_REGEX
from tessia.baselib.hypervisors.base import HypervisorBase

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

class HypervisorZvm(HypervisorBase):
    """
    This class implements the driver to support the ZVM hypervisor type
    """
    # the identifier for this hypervisor class
    HYP_ID = 'zvm'

    # names of files uploaded to zvm during netboot process
    NETBOOT_CMDLINE_FILE = 'PARMFILE PARM T'
    NETBOOT_KERNEL_FILE = 'KERNEL IMG T'
    NETBOOT_INITRD_FILE = 'INITRD IMG T'

    @validate_params
    def __init__(self, system_name, host_name, user, passwd, parameters):
        """
        Constructor

        Args:
            system_name (string): string containing the hypervisor name
            host_name (string): hostname or ip address of system
            user (string): user to login to system
            passwd (string): password to login to system
            parameters (dict): a dictionary containing values specific to each
                        hypervisor type

        Raises:
            None
        """
        # make sure here and noipl are set for the connection
        if not parameters:
            parameters = {}
        parameters['here'] = True
        parameters['noipl'] = True

        user = user.upper()
        super().__init__(system_name, host_name, user,
                         passwd, parameters)

        self._logger = get_logger(__name__)

        self._logger.debug(
            "create HypervisorZvm: name='%s' host_name='%s' user='%s' "
            "parameters='%s'",
            self.name,
            self.host_name,
            self.user,
            str(self.parameters)
        )

        # use the cms class as the connection to the zVM guest
        self._cms = GuestCms(user, host_name, user, passwd, parameters)
    # __init__()

    def _netboot(self, params):
        """
        Upload the netboot files to the zVM and perform ipl of the guest via
        the reader device.

        Args:
            params (dict): netboot parameters, see json schema for details

        Raises:
            RuntimeError: if any zVM command fails
        """
        _, re_match = self._cms.run(
            r'i cms\naccess (noprof', wait_for=['Ready;'])
        if not re_match:
            raise RuntimeError('Failed to initialize CMS')
        # make sure terminal waits before clearing the screen to prevent
        # missing content
        self._cms.run('term more 50 10', use_cp=True)

        # prepare a vdisk where we can upload the files to
        vdisk_dev = 'ffff'
        exists_msg = '(?i) {} ON '.format(vdisk_dev)
        _, re_match = self._cms.run(
            "q v {}".format(vdisk_dev),
            wait_for=[ERROR_REGEX, exists_msg], timeout=10)
        if not re_match:
            raise RuntimeError(
                'Query device {} returned unexpected output'.format(vdisk_dev))
        # no error message detected: device exists and must be detached
        if re_match.re.pattern == exists_msg:
            detached_msg = '(?i){} detached'.format(vdisk_dev)
            _, re_match = self._cms.run(
                'detach {}'.format(vdisk_dev),
                wait_for=[ERROR_REGEX, detached_msg], timeout=5)
            if not re_match:
                raise RuntimeError(
                    'Detach {} returned unexpected output'.format(vdisk_dev))
            if re_match.re.pattern == ERROR_REGEX:
                raise RuntimeError('Detach {} failed with: {}'.format(
                    vdisk_dev, re_match.group()))

        # create the vdisk with approx. 100 MB size
        defined_msg = '(?i){} defined'.format(vdisk_dev)
        _, re_match = self._cms.run(
            'define vfb-512 as ffff blk 200000',
            wait_for=[ERROR_REGEX, defined_msg], timeout=5)
        if not re_match:
            raise RuntimeError('Define vdisk returned unexpected output')
        if re_match.re.pattern == ERROR_REGEX:
            raise RuntimeError('Define vdisk failed with: {}'.format(
                re_match.group()))

        # format VDISK as file mode t
        _, re_match = self._cms.run(
            # confirm operation by typing '1' and set disk label as 'tmpdsk'
            r'format ffff t\n1\ntmpdsk', wait_for=r'(?i)Ready;',
            timeout=10)
        if not re_match:
            raise RuntimeError('Format vdisk returned unexpected output')

        # upload the kernel file
        self._cms.push_file(params['kernel_uri'], self.NETBOOT_KERNEL_FILE)
        # initrd file specified: upload it
        if params.get('initrd_uri'):
            self._cms.push_file(params['initrd_uri'], self.NETBOOT_INITRD_FILE)
        # create a temp file to hold the kernel args and upload it
        with NamedTemporaryFile(mode='w') as file_fd:
            file_fd.write(params['cmdline'])
            file_fd.flush()
            self._cms.push_file('file://{}'.format(file_fd.name),
                                self.NETBOOT_CMDLINE_FILE)

        # commands to prepare the reader device and punch the files to it
        cmds = [
            'spool punch * rdr',
            'close reader',
            'purge reader all',
            'punch {} (noh'.format(self.NETBOOT_KERNEL_FILE),
            'punch {} (noh'.format(self.NETBOOT_CMDLINE_FILE),
        ]
        if params.get('initrd_uri'):
            cmds.append('punch {} (noh'.format(self.NETBOOT_INITRD_FILE))
        cmds.append('change reader all keep')
        # reset puncher to defaults
        cmds.append('spool pun off')

        # execute all commands, abort in case of error
        wait_prompts = [r'Ready;', r'Ready\(\d+\);']
        for cmd in cmds:
            _, re_match = self._cms.run(
                cmd, wait_for=wait_prompts, timeout=300)
            if not re_match:
                raise RuntimeError(
                    "Command '{}' returned unexpected output".format(cmd))
            if re_match.re.pattern == wait_prompts[1]:
                raise RuntimeError("Command '{}' failed with: {}".format(
                    cmd, re_match.group()))

        # IPL the reader
        _, re_match = self._cms.run(
            'ipl 00c clear',
            wait_for=['Kernel command line: '], timeout=600)
        if not re_match:
            raise RuntimeError('Failed to IPL downloaded kernel')
    # _netboot()

    @staticmethod
    def _split_chars(string, size):
        """
        Split a string in sub-strings separated by space in chunks
        determined by 'size'.

        Args:
            string (str): string to split
            size (int): size of each sub-string

        Returns:
            str: resulting string containing sub-strings
        """
        index = 0
        result = []
        while index < len(string):
            result.append(string[index:index+size])
            index += size

        return ' '.join(result)
    # _split_chars()

    def login(self, timeout=60):
        """
        Execute the login to the hypervisor system using the credentials
        provided.

        Args:
            timeout (int): how many seconds to wait for connection

        Raises:
            None
        """
        self._logger.debug(
            "performing LOGIN HypervisorZvm: name='%s' host_name='%s' "
            "user='%s' parameters='%s'",
            self.name,
            self.host_name,
            self.user,
            str(self.parameters)
        )

        # login to the zVM guest
        self._cms.login()
    # login()

    def logoff(self):
        """
        Close an active connection to the hypervisor system

        Args:
            None

        Raises:
            RuntimeError: In case of fail during logoff
        """
        self._logger.debug("performing LOGOFF HypervisorZvm")

        # disconnect from zVM guest, keep the guest running
        self._cms.logoff()
    # logoff()

    def set_boot_device(self, guest_name, boot_device):
        """
        Set boot device for next load
        For ZVM it is a no-op

        Args:
            guest_name (str): guest to operate on
            boot_device (dict): boot device config
        """
        self._logger.debug(
            "performing SET_BOOT_DEVICE HypervisorZvm: name='%s', guest='%s' "
            "boot_device='%s'",
            self.name,
            guest_name,
            str(boot_device)
        )

    @validate_params
    def start(self, guest_name, cpu, memory, parameters):
        """
        Attach the given resources and IPL the guest using the method and
        device specified.

        Args:
            guest_name (str):  Name of the guest as known by hypervisor
            cpu (int):         Number of CPUs to assign
            memory (int):      Amount of memory to assign in megabytes
            parameters (dict): additional parameters, see json schema for
                               details

        Raises:
            RuntimeError: if any zVM command fails
            ValueError: - if boot method is 'disk' but no boot dev was defined
                        - if guest name is different from the username provided
                          for login
        """
        # guest to ipl is different from username: cannot continue
        if guest_name.upper() != self.user:
            msg = ('On z/VM the guest name provided must be the same as the '
                   'username specified for login')
            raise ValueError(msg)

        boot_dev = None
        if parameters['boot_method'] == 'disk':
            try:
                boot_dev = [vol for vol in parameters['storage_volumes']
                            if vol.get('boot_device')][0]
            except IndexError:
                raise ValueError("Boot method 'disk' requires a boot device")
        elif parameters['boot_method'] == 'network':
            if not 'netboot' in parameters:
                raise ValueError(
                    "Boot method 'network' requires netboot parameters")

        # put guest in a clean state
        self._cms.stop()
        self._cms.login()

        if cpu != 0:
            # clear possible attached cpus
            reset_msg = r'(?i)storage cleared - system reset'
            _, re_match = self._cms.run("detach cpu all",
                                        wait_for=[reset_msg, ERROR_REGEX],
                                        use_cp=True, timeout=10)
            # command timed out waiting for a valid output: abort as we don't
            # know the new guest state
            if not re_match:
                raise RuntimeError('Detach CPU(s) returned unexpected output')
            # HCPCPU1456E is ok because base cpu cannot be detached,
            # but with unknown error cannot continue
            if (re_match.re.pattern != reset_msg and
                    not re_match.group().startswith('HCPCPU1456E')):
                raise RuntimeError(
                    'Detach CPU(s) failed with: {}'.format(re_match.group()))

        if memory != 0:
            # attach defined memory
            stor_msg = r'STORAGE = \d+'
            _, re_match = self._cms.run("define storage {}M".format(memory),
                                        wait_for=[stor_msg, ERROR_REGEX],
                                        use_cp=True, timeout=10)
            if not re_match:
                raise RuntimeError(
                    'Define storage (memory) returned unexpected output')
            if re_match.re.pattern != stor_msg:
                raise RuntimeError('Define storage (memory) failed with: {}'
                                   .format(re_match.group()))

        # attach additional cpus and devices
        self._cms.hotplug(
            cpu=cpu-1,
            vols=parameters['storage_volumes'],
            extensions={'ifaces': parameters['ifaces']})

        # boot method 'cms': enter ipl command
        if parameters['boot_method'] == 'cms':
            _, re_match = self._cms.run(
                r'i cms\naccess (noprof', wait_for=['Ready;'])
            if not re_match:
                raise RuntimeError('Failed to IPL CMS')
            # make sure terminal waits before clearing the screen to prevent
            # missing content
            self._cms.run('term more 50 10', use_cp=True)
            return

        # boot method 'network' - presence of netboot parameters was already
        # checked
        if parameters['boot_method'] == 'network':
            self._netboot(parameters['netboot'])

        # boot device defined: perform 'disk' based ipl
        elif boot_dev:
            if boot_dev['type'] != 'fcp':
                devno = boot_dev['devno']
            # fcp device: set loaddev before ipl execution
            else:
                devno = boot_dev['adapters'][0]['devno'].split('.')[-1]
                port = self._split_chars(
                    boot_dev['adapters'][0]['wwpns'][0], 8)
                lun = self._split_chars(boot_dev['lun'], 8)
                self._cms.run(
                    'set loaddev portname {} lun {}'.format(port, lun))
                loaddev_msg = r'(?i)portname  *{}  * lun  *{}'.format(
                    port, lun)
                _, re_match = self._cms.run(
                    'q loaddev', wait_for=[loaddev_msg, ERROR_REGEX],
                    timeout=5)
                if not re_match:
                    raise RuntimeError(
                        'Query loaddev returned unexpected output')
                if re_match.re.pattern == ERROR_REGEX:
                    raise RuntimeError('Query loaddev failed with: {}'.format(
                        re_match.group()))

            _, re_match = self._cms.run('i {}'.format(
                devno), wait_for=['login: '], timeout=180)
            if not re_match:
                raise RuntimeError('Failed to IPL disk')
    # start()

    @validate_params
    def stop(self, guest_name, parameters):
        """
        Stop a given guest

        Args:
            guest_name (str): Name of the guest as known by hypervisor
            parameters (dict): currently not used

        Raises:
            ValueError: if guest name is different from the username provided
                        for login
        """
        # guest to ipl is different from username: cannot continue
        if guest_name.upper() != self.user:
            msg = ('On z/VM the guest name provided must be the same as the '
                   'username specified for login')
            raise ValueError(msg)

        self._logger.debug(
            "performing STOP HypervisorZvm: guest_name=%s "
            "parameters=%s", guest_name, str(parameters))

        # logoff from zVM guest, stop guest execution
        self._cms.stop()
    # stop()

    def reboot(self, guest_name, parameters):
        """
        Reboot a given guest

        Args:
            guest_name (str): name of the guest as known by hypervisor
            parameters (dict): currently not used

        Raises:
            NotImplementedError: currently not implemented
        """
        raise NotImplementedError()
    # reboot()
# HypervisorZvm
