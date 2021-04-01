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
Implementation of the guest interface for CMS
"""

#
# IMPORTS
#
from tempfile import NamedTemporaryFile
from tessia.baselib.common.logger import get_logger
from tessia.baselib.common.s3270.terminal import Terminal
from tessia.baselib.guests.base import GuestBase
from urllib import parse

import os
import re
import requests

#
# CONSTANTS AND DEFINITIONS
#
ERROR_REGEX = r'HCP([a-zA-Z]{0,8})\d{1,4}([E]{1})( .*)?'
TRANSFER_TIMEOUT = 600
VIRTUAL_NIC_TYPES = ('hiper', 'qdio', 'iedn', 'inmn')

#
# CODE
#

class GuestCms(GuestBase):
    """
    This class implements the driver to support the CMS guest type
    """
    # the identifier for this guest class, should be a lowercase string
    GUEST_ID = 'cms'

    def __init__(self, system_name, host_name, user, passwd, extensions):
        """
        Constructor. Initializes object variables and logging

        Args:
            system_name (str): the guest/user name
            host_name (str): hostname or ip address of guest
            user (str): the guest/user name
            passwd (str): password to access the guest
            extensions (dict): options noipl, here, byuser

        Raises:
            ValueError: in case system_name is different from username
        """
        system_name = system_name.upper()
        user = user.upper()
        if system_name.upper() != user:
            raise ValueError(
                'On zVM the guest name must be equal to the username')

        # do not ipl anything after logon as we are going to ipl cms
        if not extensions:
            extensions = {}
        extensions['noipl'] = True

        super().__init__(system_name, host_name, user, passwd, extensions)

        self._logger = get_logger(__name__)

        self._logger.debug(
            "create GuestZvm: name='%s' host_name='%s' user='%s' "
            "parameters='%s'",
            self.name,
            self.host_name,
            self.user,
            str(self.extensions)
        )

        # initialize terminal
        self._terminal = Terminal()
    # __init__()

    def _attach_cpu(self, cpus):
        """
        Add the specified number of cpus to the guest.

        Args;
            cpus (int): number of cpus to add

        Raises:
            RuntimeError: in case a zvm command fails
        """
        # list all cpus defined
        cpu_msg = r'(?i) CPU ([0-9A-Fa-f]+)'
        output, re_match = self._terminal.send_cmd(
            "q v cpus", wait_for=[ERROR_REGEX, cpu_msg], timeout=10)
        if not re_match:
            raise RuntimeError('Query CPUs returned unexpected output')
        if re_match.re.pattern == ERROR_REGEX:
            raise RuntimeError(
                'Query CPUs failed with: {}'.format(re_match.group()))

        # find last line containing cpu number in hex
        last_cpu = None
        for line in output.split('\n'):
            match_obj = re.search(cpu_msg, line)
            if match_obj:
                last_cpu = match_obj.group(1)

        self._logger.debug('Number of CPU(s) detected is: %s', last_cpu)

        last_cpu_dec = int(last_cpu, base=16)

        # define new cpus starting from last detected
        def_cpu = 'define cpu {:x}'.format(last_cpu_dec+1)
        if cpus > 1:
            def_cpu += '-{:x}'.format(last_cpu_dec+cpus)
        attach_msg = r'(?i)cpu [0-9A-Fa-f]+ defined'
        _, re_match = self._terminal.send_cmd(
            def_cpu, wait_for=[attach_msg, ERROR_REGEX], timeout=10)
        if not re_match:
            raise RuntimeError('Define CPU(s) returned unexpected output')
        if re_match.re.pattern == ERROR_REGEX:
            raise RuntimeError(
                'Define CPU(s) failed with: {}'.format(re_match.group()))
    # _attach_cpu()

    def _attach_dev(self, dev_id, dev_type):
        """
        Attach a ccw or pci device to the guest

        Args:
            dev_id (str): ccw channel or pci id
            dev_type (str): 'ccw' or 'pci'

        Raises:
            RuntimeError: in case a zvm command fails
        """
        query_msgs = [ERROR_REGEX]
        if dev_type == 'pci':
            dev_type = 'pcif'
            query_msgs.append('(?i) A PCI function was not found')
            query_msgs.append('(?i) PCIF 0*{} ON '.format(dev_id))
        else:
            dev_type = ''
            query_msgs.append('(?i) {} ON '.format(dev_id))

        # if device is already attached the operation is skipped, with that
        # approach we make sure not to fail in case the device was already
        # defined as virtual by user directory
        _, re_match = self._terminal.send_cmd(
            "q v {} {}".format(dev_type, dev_id),
            wait_for=query_msgs, timeout=10)
        if not re_match:
            raise RuntimeError(
                'Query device {} returned unexpected output'.format(dev_id))
        if re_match.re.pattern == query_msgs[-1]:
            self._logger.info(
                'Device %s already defined, skipping attach', dev_id)
            return

        # set regexes for the successful cases
        attached_msg = '(?i){} attached to {}'.format(dev_id, self.name)
        already_msg = '(?i){} already attached to {}'.format(
            dev_id, self.name)
        # issue attach command
        _, re_match = self._terminal.send_cmd(
            "att {} {} *".format(dev_type, dev_id),
            wait_for=[attached_msg, already_msg, ERROR_REGEX], timeout=30)
        if not re_match:
            raise RuntimeError('Attach device {} returned unexpected output'
                               .format(dev_id))
        if re_match.re.pattern not in (attached_msg, already_msg):
            raise RuntimeError('Attach device {} failed with: {}'.format(
                dev_id, re_match.group()))
    # _attach_dev()

    def _attach_iface(self, iface_dict):
        """
        Attach a network interface to the guest.

        Args:
            iface_dict (dict): dict with iface properties 'id', 'type' and
                               additional 'count', 'system' for virtual ifaces

        Raises:
            ValueError: in case an unsupported iface type is specified
        """
        if iface_dict['type'] in ('osa', 'hsi'):
            ch_list = iface_dict['id'].split(',')
            for channel in ch_list:
                self._attach_dev(channel, 'ccw')
        elif iface_dict['type'] == 'pci':
            self._attach_dev(iface_dict['id'], 'pci')
        elif iface_dict['type'] in VIRTUAL_NIC_TYPES:
            self._define_nic(iface_dict['id'], iface_dict['type'],
                             iface_dict['count'], iface_dict['system'])
        else:
            raise ValueError("Unsupported network interface type '{}'".format(
                iface_dict['type']))
    # _attach_iface()

    def _define_nic(self, address, dev_type, dev_count, target_system):
        """
        Create a virtual network interface.

        Args:
            address (str): device address to define
            dev_type (str): one of VIRTUAL_NIC_TYPES
            dev_count (int): how many devices to define
            target_system (str): system to couple to

        Raises:
            RuntimeError: in case a zvm command fails
        """
        # first step: define virtual device
        defined_msg = (r'(?i)NIC {0} is created; devices {0}-.+ defined'
                       .format(address))
        _, re_match = self._terminal.send_cmd(
            "define nic {} {} devices {}".format(
                address, dev_type, dev_count),
            wait_for=[defined_msg, ERROR_REGEX],
        )
        if not re_match:
            raise RuntimeError('Define device {} returned unexpected output'
                               .format(address))
        if re_match.re.pattern == ERROR_REGEX:
            raise RuntimeError('Define device {} failed with: {}'
                               .format(address, re_match.group()))

        # second step: couple defined nic to the virtual switch
        coupled_msg = r'(?i)NIC {} is connected to SYSTEM'.format(address)
        _, re_match = self._terminal.send_cmd(
            "couple {} to SYSTEM {}".format(address, target_system),
            wait_for=[coupled_msg, ERROR_REGEX],
        )
        if not re_match:
            raise RuntimeError('Couple nic {} returned unexpected output'
                               .format(address))
        if re_match.re.pattern == ERROR_REGEX:
            raise RuntimeError('Couple nic {} failed with: {}'
                               .format(address, re_match.group()))
    # _define_nic()

    def hotplug(self, cpu=None, memory=None, vols=None, extensions=None):
        """
        Attaches cpus, disks or network interfaces.

        Args:
            cpu (int): number of new cpus to activate
            memory (int): None (currently not supported)
            vols (list): list of vols in the form [{'devno': 'ffff'}]
            extensions (dict): when key 'ifaces' with a list is present,
                attach network interfaces. See _attach_iface for format of
                dict in the list.

        Raises:
            NotImplementedError: in case memory hotplug is attempted
        """
        if cpu and cpu > 0:
            self._attach_cpu(cpu)
        if memory:
            raise NotImplementedError()
        if vols:
            for vol in vols:
                if vol['type'] != 'fcp':
                    self._attach_dev(vol['devno'].split('.')[-1], 'ccw')
                else:
                    for adapter in vol['adapters']:
                        self._attach_dev(
                            adapter['devno'].split('.')[-1], 'ccw')
        if extensions is not None and 'ifaces' in extensions:
            for iface in extensions['ifaces']:
                self._attach_iface(iface)
    # hotplug()

    def login(self, timeout=60):
        """
        Execute the login to the guest system using the credentials
        provided in the constructor.

        Args:
            timeout (int): how many seconds to wait for connection

        Raises:
            RuntimeError: in case ipl of CMS fails
        """
        self._logger.debug(
            "performing LOGIN GuestZvm: name='%s' host_name='%s' "
            "user='%s' parameters='%s'",
            self.name,
            self.host_name,
            self.user,
            str(self.extensions)
        )

        output = self._terminal.login(
            self.host_name, self.user, self.passwd, self.extensions, timeout
        )
        cms_output, re_match = self._terminal.send_cmd(
            r'i cms\naccess (noprof', use_cp=True, wait_for=['Ready;'])
        if not re_match:
            raise RuntimeError('Failed to IPL CMS')
        # make sure terminal waits before clearing the screen to prevent
        # missing content
        self._terminal.send_cmd('term more 50 10', use_cp=True)

        self._logger.debug("LOGIN process: \n%s", output+cms_output)
    # login()

    def logoff(self):
        """
        Close an active connection to the guest system. Note: although called
        logoff, this method performs a disconnect so that the guest keeps
        running. Use the method 'stop' for a real logoff.

        Args:
            None

        Raises:
            RuntimeError: if operation fails
        """
        self._logger.debug("performing LOGOFF GuestZvm")
        self._terminal.disconnect()
    # logoff()

    def install_packages(self, packages):
        """
        Use the system's package management facilities and install the
        specified packages. Currently not supported.

        Args:
            packages (list): package names to install

        Raises:
            NotImplementedError: not supported
        """
        raise NotImplementedError()
    # install_packages()

    def open_session(self, extensions=None):
        """
        Given the fact that CMS does not support multiple sessions calling this
        method will result in error.

        Args:
            extensions (dict): None

        Raises:
            OSError: as it is not supported
        """
        raise OSError('CMS does not support multiple sessions')
    # open_session()

    def pull_file(self):
        """
        TODO
        """
        raise NotImplementedError()
    # pull_file()

    def push_file(self, source_url, target_path, write_mode='binary'):
        """
        Retrieve a file from 'source_url' and copy it to a file 'target_path'
        on the guest.

        Args:
            source_url (str): url where the source file should be copied from.
                              The following schemes are accepted:
                              file:///target/path (local file)
                              http, https or ftp urls
            target_path (str): target filepath on the guest in zVM form
                (i.e. FILENAME TYPE A)
            write_mode (str): Either 'binary' or 'ascii'

        Raises:
            ValueError: invalid url type or source url not found/reachable
        """
        parsed_url = parse.urlsplit(source_url)
        scheme = parsed_url.scheme
        transfer_parameters = {}
        if 'transfer-buffer-size' in self.extensions:
            transfer_parameters['BufferSize'] = self.extensions.get(
                'transfer-buffer-size')

        # source is a local file: read it and push it
        if scheme == 'file':
            local_path = parse.unquote(parsed_url.path, errors='strict')
            if not os.path.exists(local_path):
                raise ValueError(
                    "Local file '{}' does not exist.".format(local_path))
            self._terminal.transfer(
                local_path, target_path, direction='send',
                timeout=TRANSFER_TIMEOUT, mode=write_mode,
                **transfer_parameters)

        # source is a http[s] or ftp URL: download it first to a local file
        elif scheme in ['http', 'https', 'ftp']:
            try:
                resp = requests.get(source_url, stream=True, verify=False)
                resp.raise_for_status()
            except requests.exceptions.RequestException as exc:
                raise ValueError(
                    "Source url is not accessible: {} {}".format(
                        exc.response.status_code, exc.response.reason))

            # download the file
            with NamedTemporaryFile(mode='wb') as file_fd:
                chunk_size = 10 * 1024
                for chunk in resp.iter_content(chunk_size=chunk_size):
                    file_fd.write(chunk)
                file_size = file_fd.tell()
                extra_zeros_size = 80 - (file_size % 80)
                file_fd.write(b'\0' * extra_zeros_size)
                file_fd.flush()
                # transfer downloaded file to host
                self._terminal.transfer(
                    file_fd.name, target_path, direction='send',
                    timeout=TRANSFER_TIMEOUT, mode=write_mode,
                    **transfer_parameters)

        # any other scheme: not supported
        else:
            raise ValueError('Invalid url scheme for push operation')

    # push_file()

    def run(self, cmd, **extensions):
        """
        Execute a command on the s3270 terminal.

        Args:
            cmd (str): command to be executed
            extensions (any): any additional parameters supported by the
                underlying Terminal module

        Returns:
            tuple: collected output, matched regex object (or None if no match)
        """
        if not extensions:
            extensions = {}
        return self._terminal.send_cmd(cmd, **extensions)
    # run()

    def stop(self):
        """
        Stop the guest by executing a system clear and logoff
        """
        self._logger.debug(
            "performing STOP GuestZvm: guest_name=%s "
            "parameters=%s", self.name, str(self.extensions))

        # clear system memory before logoff
        self._terminal.send_cmd("system clear", True)

        # logoff from guest
        self._terminal.logoff()
    # stop()
# GuestCms
