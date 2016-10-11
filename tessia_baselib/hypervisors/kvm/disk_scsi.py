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
Module for DiskScsi class.
"""
#
# IMPORTS
#
from tessia_baselib.common.logger import get_logger
from tessia_baselib.common.utils import timer
from tessia_baselib.hypervisors.kvm.disk import DiskBase
from time import sleep

#
# CONSTANTS AND DEFINITIONS
#
FCP_SYSPATH = '/sys/bus/ccw/drivers/zfcp'
FCP_DEVPATH = '/dev/disk/by-path/ccw-{}-zfcp-{}:{}'

#
# CODE
#
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

def _get_zfcp_dev_path(devno, wwpn, lun):
    """
    Auxiliary function. Get the full zfcp device path.

    Args:
        devno (str): device number of the zfcp adapter.
        wwpn (str): worldwide port number used to access the device.
        lun (str): lun of the device.

    Returns:
        str: full device path.

    Raises:
        None
    """
    dev_path = FCP_DEVPATH.format(devno, wwpn, lun)

    return dev_path
# _get_zfcp_dev_path()

def _get_all_multipath_dev_paths(paths, lun):
    """
    Auxiliary method. Generate the path for all the devices in a multipath
    schema.

    Args:
        paths (dict):  A path as defined in the json schema.
        lun   (str):   The lun.

    Returns:
        list:  A list contaning the full path for all devices in a multipath
                   schema.

    Raises:
        None
    """
    path_devs = []

    for path in paths:
        zfcp_devno = path["devno"]
        for wwpn in path["wwpns"]:
            path_dev = _get_zfcp_dev_path(zfcp_devno, wwpn, lun)
            path_devs.append(path_dev)

    return path_devs
# _get_all_multipath_dev_paths()

class DiskScsi(DiskBase):
    """
    This class is an abstraction for a scsi disk.
    """
    def __init__(self, parameters, target_dev_mngr, cmd_channel):
        """
        Constructor

        Args:
            parameters (dict):  Disk parameters as defined in the json schema.
            target_dev_mngr (object): Instance of TargetDeviceManager.
            cmd_channel (object): An object that provides a method in the
                                  format "run(self, cmd, timeout=120):".
                                  This method is used to perform commands in
                                  the host ir order to handledisk operations.

        Returns:
            None

        Raises:
            None
        """

        super().__init__(parameters, target_dev_mngr, cmd_channel)

        self._logger = get_logger(__name__)

        self._lun = self._parameters.get("volume_id")
        self._multipath = self._parameters.get("specs").get("multipath")
        self._paths = self._parameters.get("specs").get("paths")

        self._logger.debug("Creating DiskScsi "
                           "lun=%s paths=%s", self._lun, self._paths)

        self._devmap = None
    # __init__()

    def _enable_zfcp_module(self):
        """
        Auxiliary method. Enable the zfcp module.

        Args:
            None

        Returns:
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

    def _is_wwpn_active(self, devno, wwpn):
        """
        Auxiliary method. Verify if the wwpn is active in the zfcp
        interface.

        Args:
            devno (str): Device number of the zfcp interface.
            wwpn (str):  wwpn to be verified as active.

        Returns:
            bool: True in case the wwpn is active. False otherwise.

        Raises:
            None
        """
        adapter_path = _get_adapter_path(devno)
        cmd = "[ -e '{}/{}' ]".format(adapter_path, wwpn)
        ret, _ = self._cmd_channel.run(cmd)

        return ret == 0
    # _is_wwpn_active()

    def _activate_wwpn(self, devno, wwpn):
        """
        Auxiliary method. Activate a wwpn.

        Args:
            devno (str): device number of the zfcp interface.
            wwpn (str):  wwpn to be activated.

        Returns:
            None

        Raies:
            None
        """
        self._logger.debug("Activating wwpn %s on zfcp"
                           " adapter %s", devno, wwpn)

        adapter_path = _get_adapter_path(devno)
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
        Auxiliary method. Check that the zfcp adapter is active.

        Args:
            devno (str): Device number of the zfcp adapter.

        Returns:
            None

        Raises:
            None
        """
        cmd = "[ -e '{}/{}' ]".format(FCP_SYSPATH, devno)
        error_msg = 'Adapter {} could not be activated'.format(devno)
        timer(self._cmd_channel, cmd, [0, 1, 3, 5, 30], error_msg)
    # _check_adapter_active()

    def _is_lun_active(self, devno, wwpn, lun):
        """
        Auxiliary method. check if the lun is active.

        Args:
            devno (str): device number of the zfcp adapter.
            wwpn (str):  worldwide port number used to access the device.
            lun (str):   lun of the disk.
        Returns:
            bool: True in case the lun is active. False otherwise.

        Raises:
            None
        """
        path_dev = _get_zfcp_dev_path(devno, wwpn, lun)
        ret, _ = self._cmd_channel.run("readlink -e '{}'".format(path_dev))

        return ret == 0
    # _is_lun_active()

    def _activate_lun(self, devno, wwpn, lun):
        """
        Auxiliary method. activate the lun.

        Args:
            devno (str): device number of the zfcp adapter.
            wwpn (str): worldwide port number used to access the device.
            lun (str): lun of the device.

        Returns:
            None

        Raises:
            RuntimeError: In case the LUN fails to be add to the wwpn.
        """
        self._logger.debug("Activating LUN %s for wwpn %s "
                           "on adapter %s", lun, wwpn, devno)

        adapter_path = _get_adapter_path(devno)
        path_dev = _get_zfcp_dev_path(devno, wwpn, lun)
        cmd = "echo '{}' > {}/{}/unit_add".format(lun, adapter_path, wwpn)
        ret, output = self._cmd_channel.run(cmd)

        if ret != 0:
            raise RuntimeError("Failed to activate LUN {}"
                               " in WWPN {}:{}".format(lun, wwpn, output))

        # FCP adapter might have delays so give some time to scsi
        # device to come up (see bz #121346)
        cmd = "readlink -e '{}'".format(path_dev)
        try:
            timer(self._cmd_channel, cmd, [1, 5, 15, 30, 60], '')
        except RuntimeError:
            # try to be helpful and report storage configuration
            # problem if failed is 1
            cmd = 'cat {}/{}/{}/failed'.format(adapter_path, wwpn,
                                               lun)
            ret, output = self._cmd_channel.run(cmd)
            if ret == 0 and output.strip() == '1':
                msg = ("Failed to add LUN {} under {}/{}, check your "
                       'storage configuration'.format(lun,
                                                      devno, wwpn))
            else:
                msg = ("Device {} didn't come "
                       "up after adding LUN".format(path_dev))
            raise RuntimeError(msg)
    # _activate_lun()

    def _enable_path(self, path):
        """
        Auxiliary method. Enable a path.

        Args:
            path (dict): A dictionary containing a path, as specified
                         in the json schema.

        Returns:
            None

        Raises:
            None.
        """
        #enable the fcp adapter
        self._logger.debug("Enabling path %s", path)

        zfcp_devno = path["devno"]
        self._enable_device(zfcp_devno)
        self._check_adapter_active(zfcp_devno)
        #iterate over each wwpn of an zfcp adapter
        for wwpn in path['wwpns']:
            if not self._is_wwpn_active(zfcp_devno, wwpn):
                self._activate_wwpn(zfcp_devno, wwpn)

            if not self._is_lun_active(zfcp_devno, wwpn, self._lun):
                self._activate_lun(zfcp_devno, wwpn, self._lun)
    # _enable_path()

    def _get_kernel_devname(self, dev):
        """
        Auxiliary method. get the device name based on the link generated
        by udev.

        Args:
            dev (str): Device path generated by udev.

        Returns:
            str: Device path.

        Raises:
            RuntimeError: In case the link does not exists.
        """
        # resolve symlink
        cmd = "readlink -e '{}'".format(dev)
        ret, output = self._cmd_channel.run(cmd)

        if ret != 0:
            raise RuntimeError('Kernel device does exist for {}'.format(dev))

        return output.strip()
    # _get_kernel_devname()

    def _get_multipath_name(self, path_dev):
        """
        Auxiliary method. Get the multipath device based on a path.

        Args:
            path_dev (str): Full path to a device that is part of the
                            multipath.

        Returns:
            str: Path to the multipath device mapper.

        Raises:
            None
        """
        #makes sure we are using the path to the device
        kernel_dev = self._get_kernel_devname(path_dev)

        for time in (0, 1, 5, 15, 30, 60):
            sleep(time)
            cmd = 'multipath -v 1 -l {}'.format(kernel_dev)
            ret, output = self._cmd_channel.run(cmd)
            output = output.strip()

            if ret == 0 and len(output) > 0:
                return output

        return None
    # _get_multipath_name()

    def _get_dm_dev(self, devmap):
        """
        Auxiliary Method. Get the name of the device being used by
        the device mapper.

        Args:
            devmap (str): Device mapper name.

        Returns:
            str: Kernel device name of the device mapped.

        Raises:
            None
        """
        for time in (0, 1, 5, 15, 30, 60):
            sleep(time)
            try:
                # TODO this makes sense?
                mpath_dm_dev = self._get_kernel_devname(
                    '/dev/mapper/{}'.format(devmap)).split('/')[-1]
                return mpath_dm_dev
            except RuntimeError:
                pass
        return None
    # _get_dm_dev()

    def _check_multipath(self):
        """
        Auxiliary method. Checks that each path belongs to the same
        multipath name.

        Args:
            None

        Returns:
            None

        Raises:
            RuntimeError: In case the paths are not part of a multipath name,
                          or the multipath name is not part of a device mapper,
                          or the multipath name is not the same across all
                          disks.
        """
        mpath_name = None
        #the multipath device mapper device
        mpath_dm_dev = None

        path_devs = _get_all_multipath_dev_paths(self._paths, self._lun)

        self._logger.debug("Checking if the following paths"
                           " belongs to the same multipath "
                           "name: %s", path_devs)
        #iterate over each device path that is part of the multipath
        for path_dev in path_devs:
            kernel_dev = self._get_kernel_devname(path_dev)
            checked_mpath_name = self._get_multipath_name(path_dev)

            # path is not part of any mpath map
            if checked_mpath_name is None:
                msg = ("Multipath map not available for device {}, perhaps "
                       "it's blacklisted?".format(path_dev))
                raise RuntimeError(msg)

            # first path verification: store mpath name for validation against
            # next paths
            if mpath_name is None:
                mpath_name = checked_mpath_name
                # the device mapper name (i.e. dm-0)
                mpath_dm_dev = self._get_dm_dev(mpath_name)
                if mpath_dm_dev is None:
                    raise RuntimeError("Failed to determine device mapper for "
                                       "multipath "
                                       "/dev/mapper/{}".format(mpath_name))
            # mpath map is different from previous path: this should never
            # happen
            elif checked_mpath_name != mpath_name:
                raise RuntimeError("Multipath map is not the same"
                                   " across paths of disk {}".format(
                                       self._lun))

            # make sure the path is monitored by the map
            msg = ("Device {} not monitored by "
                   "multipath map {}".format(path_dev, mpath_name))
            cmd = ("[ -e '/sys/block/{}/slaves/{}' ]".format(
                mpath_dm_dev, kernel_dev.split('/')[-1]))
            timer(self._cmd_channel, cmd, [0, 1, 5, 15, 30, 60], msg)

        #update the source dev
        self._source_dev = "/dev/mapper/" + mpath_name
    # _check_multipath()

    def _disable_multipath(self):
        """
        Auxiliary method. Remove each disk path from multipath map.

        Args:
            None

        Returns:
            None

        Raises:
            None
        """
        self._logger.debug("Disabling multipath")
        path_devs = _get_all_multipath_dev_paths(self._paths, self._lun)

        for path_dev in path_devs:
            kernel_dev = self._get_kernel_devname(path_dev)
            cmd = 'multipathd del path {}'.format(kernel_dev)
            msg = 'Failed to disable multipath for device {}'.format(path_dev)
            timer(self._cmd_channel, cmd, [0, 1, 5, 15, 30, 60], msg)
    # _disable_multipath()

    def activate(self):
        """
        Activate the disk by performing all necessary operations to get
        the block device avaiable in the hypervisor operating system.

        Args:
            None

        Returns:
            None

        Raises:
            None
        """
        self._enable_zfcp_module()

        #enable each path
        #Iterate over each zfcp adapter
        for path in self._paths:
            self._enable_path(path)

        if self._multipath:
            self._check_multipath()
        else:
            self._disable_multipath()
    # activate()
# DiskScsi
