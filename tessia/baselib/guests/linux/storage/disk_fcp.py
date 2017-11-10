# Copyright 2017 IBM Corp.
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
Module for DiskFcp class.
"""
#
# IMPORTS
#
from copy import deepcopy
from tessia.baselib.common.logger import get_logger
from tessia.baselib.common.utils import timer
from tessia.baselib.guests.linux.storage.disk import DiskBase
from time import sleep

#
# CONSTANTS AND DEFINITIONS
#
FCP_SYSPATH = '/sys/bus/ccw/drivers/zfcp'

#
# CODE
#
class DiskFcp(DiskBase):
    """
    This class is an abstraction for a FCP-SCSI disk.
    """
    def __init__(self, parameters, host_conn):
        """
        Constructor

        Args:
            parameters (dict):  Disk parameters as defined in the json schema.
            host_conn (GuestLinux): instance connected to linux host

        Raises:
            ValueError: in case no fcp path is provided
        """

        super().__init__(parameters, host_conn)

        self._logger = get_logger(__name__)

        # the lun id, i.e. 1022400000000002 (no leading 0x)
        self._lun = '0x{}'.format(self._parameters.get("volume_id"))

        # whether multipath is enabled (True or False)
        self._multipath = self._parameters["specs"].get("multipath", False)

        # list of adapters with paths - mandatory, at least one path must be
        # specified otherwise it's not possible to activate disk
        has_path = False
        self._adapters = deepcopy(self._parameters["specs"]["adapters"])
        # add the leading 0x to the wwpns
        for adapter in self._adapters:
            for i in range(0, len(adapter.get('wwpns', []))):
                has_path = True
                adapter['wwpns'][i] = '0x{}'.format(adapter['wwpns'][i])

        if not has_path:
            raise ValueError(
                'No FCP path defined for disk LUN {}'.format(self._lun))

        self._logger.debug("Creating DiskFcp "
                           "lun=%s adapters=%s", self._lun, self._adapters)
    # __init__()

    def _enable_zfcp_module(self):
        """
        Auxiliary method. Enable the zfcp module.

        Args:
            None

        Raises:
            RuntimeError: In case there is a error while loading the zfcp
                          module.
        """
        self._logger.debug("Enabling zfcp module")

        ret, out = self._cmd_channel.run("modprobe zfcp")

        if ret != 0:
            raise RuntimeError("Unable to load fcp module: {}".format(out))
    # _enable_zfcp_module()

    @staticmethod
    def _get_adapter_path(devno):
        """
        Auxiliary function. Get the device path for the fcp adapter.

        Args:
            devno (str):  Device number of the fcp adapter.

        Returns:
            str: Path to the device.

        Raises:
            None
        """
        adapter_path = '{}/{}'.format(FCP_SYSPATH, devno)

        return adapter_path
    # _get_adapter_path()

    def _get_all_scsi_dev_filenames(self, adapters, lun):
        """
        Auxiliary method. Generate the device filenames for each fcp path of
        the lun and adapters specified as arguments.

        Args:
            adapters (list): adapter entries as defined in the json schema.
            lun (str): the lun id.

        Returns:
            list: A list contaning the device filename for all paths of the
                  adapters

        Raises:
            None
        """
        scsi_devs = []

        for adapter in adapters:
            zfcp_devno = adapter["devno"]
            for wwpn in adapter["wwpns"]:
                entry = {
                    'fcp_path': '{}/{}/{}'.format(zfcp_devno, wwpn, lun),
                    'kernel_path': self._get_scsi_dev_filename(
                        zfcp_devno, wwpn, lun)
                }
                scsi_devs.append(entry)

        return scsi_devs
    # _get_all_scsi_dev_filenames()

    def _get_scsi_dev_filename(self, devno, wwpn, lun):
        """
        Auxiliary function, returns the kernel device filename of a lun path.

        Args:
            devno (str): device number of the zfcp adapter.
            wwpn (str): worldwide port number used to access the device.
            lun (str): lun of the device.

        Returns:
            str: full device path.

        Raises:
            RuntimeError: in case scsi kernel device cannot be determined
        """
        # retrieve the scsi path associated with the fcp path
        cmd = "lszfcp -D -b {} -p {} -l {}".format(devno, wwpn, lun)
        ret, output = self._cmd_channel.run(cmd)
        output = output.strip()
        if ret != 0 or not output:
            raise RuntimeError('scsi path not found for '
                               'path {}/{}/{}'.format(devno, wwpn, lun))
        scsi_path = output.split()[-1]

        # convert scsi path to kernel device
        ret, output = self._cmd_channel.run('lsscsi {}'.format(scsi_path))
        output = output.strip()
        if ret != 0 or not output:
            raise RuntimeError('scsi kernel device not found for '
                               'path {}/{}/{}'.format(devno, wwpn, lun))

        return output.split()[-1]
    # _get_scsi_dev_filename()

    def _is_wwpn_active(self, devno, wwpn):
        """
        Auxiliary method. Verify if the wwpn is active in the zfcp adapter.

        Args:
            devno (str): Device number of the zfcp adapter.
            wwpn (str):  wwpn to be verified as active.

        Returns:
            bool: True in case the wwpn is active. False otherwise.

        Raises:
            None
        """
        adapter_path = self._get_adapter_path(devno)
        cmd = "[ -e '{}/{}' ]".format(adapter_path, wwpn)
        ret, _ = self._cmd_channel.run(cmd)

        return ret == 0
    # _is_wwpn_active()

    def _activate_wwpn(self, devno, wwpn):
        """
        Auxiliary method. Activate a wwpn.

        Args:
            devno (str): device number of the zfcp adapter.
            wwpn (str):  wwpn to be activated.

        Raies:
            None
        """
        self._logger.debug(
            "Activating wwpn %s on zfcp" " adapter %s", wwpn, devno)

        adapter_path = self._get_adapter_path(devno)
        cmd = "[ -e '{}/port_add' ]".format(adapter_path)
        ret, _ = self._cmd_channel.run(cmd)

        # old zfcp interface: add port manually
        if ret == 0:
            self._cmd_channel.run("echo '{}' >"
                                  " {}/port_add".format(wwpn, adapter_path))
        # new zfcp interface: in the unlikely scenario that someone
        # accidentally removed manually the port try a port rescan
        else:
            self._cmd_channel.run("[ -e '{}/port_rescan' ] && echo 1 > "
                                  "{}/port_rescan".format(adapter_path,
                                                          adapter_path))

        # verify if it's available now
        cmd = "[ -e '{}/{}' ]".format(adapter_path, wwpn)
        error_msg = (
            'Failed to add port {} to adapter {}, check your '
            'storage configuration'.format(wwpn, devno))
        timer(self._cmd_channel, cmd, [0, 1, 3, 5, 30],
              error_msg)
    # _activate_wwpn()

    def _check_adapter_active(self, devno):
        """
        Auxiliary method. Wait for a period until the zfcp adapter is active.

        Args:
            devno (str): Device number of the zfcp adapter.

        Raises:
            None
        """
        cmd = "[ -e '{}' ]".format(self._get_adapter_path(devno))
        error_msg = 'Adapter {} could not be activated'.format(devno)
        timer(self._cmd_channel, cmd, [0, 1, 3, 5, 30], error_msg)
    # _check_adapter_active()

    def _is_lun_active(self, devno, wwpn, lun):
        """
        Auxiliary method. Check if the lun is active.

        Args:
            devno (str): device number of the zfcp adapter.
            wwpn (str):  worldwide port number used to access the device.
            lun (str):   lun of the disk.

        Returns:
            bool: True in case the lun is active. False otherwise.

        Raises:
            None
        """
        try:
            self._get_scsi_dev_filename(devno, wwpn, lun)
        except RuntimeError:
            return False

        return True
    # _is_lun_active()

    def _activate_lun(self, devno, wwpn, lun):
        """
        Auxiliary method. Activate the lun.

        Args:
            devno (str): device number of the zfcp adapter.
            wwpn (str): worldwide port number used to access the device.
            lun (str): lun of the device.

        Raises:
            RuntimeError: In case the LUN fails to be added to the wwpn.
        """
        self._logger.debug(
            "Activating LUN %s for wwpn %s on adapter %s", lun, wwpn, devno)

        # build the filesystem paths for the adapter and lun's path
        adapter_path = self._get_adapter_path(devno)

        # execute the action to attach the lun
        cmd = "echo '{}' > {}/{}/unit_add".format(lun, adapter_path, wwpn)
        ret, output = self._cmd_channel.run(cmd)
        if ret != 0:
            raise RuntimeError("Failed to activate LUN {}"
                               " in WWPN {}:{}".format(lun, wwpn, output))

        # FCP adapter might have delays so give some time for device
        # to come up in the kernel
        found = False
        for time in (0, 1, 5, 15, 30, 60):
            sleep(time)
            try:
                self._get_scsi_dev_filename(devno, wwpn, lun)
            except RuntimeError:
                continue
            found = True
            break
        if not found:
            # try to be helpful and report storage configuration
            # problem if failed is 1
            cmd = 'cat {}/{}/{}/failed'.format(adapter_path, wwpn,
                                               lun)
            ret, output = self._cmd_channel.run(cmd)
            if ret == 0 and output.strip() == '1':
                msg = ("Failed to add LUN {} under {}/{}, check your "
                       'storage configuration'.format(lun, devno, wwpn))
            else:
                msg = ("FCP path {}/{}/{} didn't come "
                       "up after adding LUN".format(devno, wwpn, lun))
            raise RuntimeError(msg)
    # _activate_lun()

    def _enable_lun_paths(self, adapter):
        """
        Auxiliary method. Enable each lun path of an adapter.

        Args:
            adapter (dict): A dictionary containing adapter devno and paths,
                            as specified in the json schema.

        Raises:
            None.
        """
        # enable the fcp adapter
        self._logger.debug("Enabling for lun %s the paths %s",
                           self._lun, adapter)

        zfcp_devno = adapter["devno"]
        # activate the adapter
        self._enable_device(zfcp_devno)
        # wait for a while for the device to come up in the kernel
        self._check_adapter_active(zfcp_devno)
        # add each path of an adapter by iterating over the wwpns
        for wwpn in adapter['wwpns']:
            if not self._is_wwpn_active(zfcp_devno, wwpn):
                self._activate_wwpn(zfcp_devno, wwpn)

            if not self._is_lun_active(zfcp_devno, wwpn, self._lun):
                self._activate_lun(zfcp_devno, wwpn, self._lun)
    # _enable_lun_paths()

    def _get_kernel_devname(self, dev):
        """
        Auxiliary method. Get the device name based on the symlink generated
        by udev.

        Args:
            dev (str): Device symlink generated by udev.

        Returns:
            str: Device filepath.

        Raises:
            RuntimeError: In case the symlink is broken.
        """
        # resolve symlink
        cmd = "readlink -e '{}'".format(dev)
        ret, output = self._cmd_channel.run(cmd)

        if ret != 0:
            raise RuntimeError(
                'Kernel device does exist for symlink {}'.format(dev))

        return output.strip()
    # _get_kernel_devname()

    def _get_multipath_name(self, path_dev):
        """
        Auxiliary method. Get the multipath device associated with a given
        path.

        Args:
            path_dev (str): Full filepath to a device that is part of the
                            multipath.

        Returns:
            str: Path to the device mapper representing the multipath map, or
                 None if no multipath map is associated with the given path.

        Raises:
            None
        """
        # makes sure we are using the device file and not a symlink
        kernel_dev = self._get_kernel_devname(path_dev)

        # use a timer because multipath daemon might have delays to reflect
        # the commands
        for time in (0, 1, 5, 15, 30, 60):
            sleep(time)
            cmd = 'multipath -v 1 -l {}'.format(kernel_dev)
            ret, output = self._cmd_channel.run(cmd)
            output = output.strip()

            if ret == 0 and output:
                return output

        return None
    # _get_multipath_name()

    def _check_multipath(self):
        """
        Auxiliary method. Checks that each path belongs to the same
        multipath map.

        Args:
            None

        Returns:
            str: device path associated to multipath

        Raises:
            RuntimeError: In case the paths are not part of a multipath map,
                          or the multipath map is not part of a device mapper,
                          or the multipath map is not the same across all
                          paths.
        """
        # the name of the multipath map associated with the paths
        mpath_name = None

        scsi_devs = self._get_all_scsi_dev_filenames(self._adapters, self._lun)

        self._logger.debug("Checking if the following devices belong to the "
                           "same multipath name: %s", scsi_devs)
        # perform verification on each device filename that is supposed to be
        # part of the multipath map
        for scsi_dev in scsi_devs:
            # find the multipath map associated with this path
            check_mpath_name = self._get_multipath_name(
                scsi_dev['kernel_path'])

            # path is not part of any mpath map: report storage problem
            if check_mpath_name is None:
                msg = ("Multipath map not available for path {}, make sure "
                       "it's not blacklisted".format(scsi_dev['fcp_path']))
                raise RuntimeError(msg)

            # first path verification: store mpath map name for validation
            # against next paths
            if mpath_name is None:
                mpath_name = check_mpath_name

            # mpath map is different from previous path: this should never
            # happen
            elif check_mpath_name != mpath_name:
                raise RuntimeError("Multipath map is not the same across "
                                   "paths of lun {}".format(self._lun))

        # return the device path of the multipath mapping
        return "/dev/mapper/" + mpath_name
    # _check_multipath()

    def _disable_multipath(self):
        """
        Auxiliary method. Remove each disk path from its multipath map.

        Args:
            None

        Returns:
            str: device path of first LUN path

        Raises:
            None
        """
        scsi_devs = self._get_all_scsi_dev_filenames(self._adapters, self._lun)
        self._logger.debug("Disabling multipath for devices: %s", scsi_devs)

        for scsi_dev in scsi_devs:
            cmd = 'multipathd del path {}'.format(scsi_dev['kernel_path'])
            msg = ('Failed to disable multipath for device {} path {}'
                   .format(scsi_dev['kernel_path'], scsi_dev['fcp_path']))
            timer(self._cmd_channel, cmd, [0, 1, 5, 15, 30, 60], msg)

        # return the device path as the first lun path
        return scsi_devs[0]['kernel_path']
    # _disable_multipath()

    def activate(self):
        """
        Activate the disk by performing all necessary operations to get
        the block device avaiable in the hypervisor operating system.

        Args:
            None

        Returns:
            str: device path of the activated disk

        Raises:
            None
        """
        self._enable_zfcp_module()

        # enable each lun path by iterating over the zfcp adapters
        for adapter in self._adapters:
            self._enable_lun_paths(adapter)

        if self._multipath:
            dev_path = self._check_multipath()
        else:
            dev_path = self._disable_multipath()

        return dev_path
    # activate()
# DiskFcp
