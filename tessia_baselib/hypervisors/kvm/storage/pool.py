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
Handles a pool of disks for a kvm guest
"""

#
# IMPORTS
#
from tessia_baselib.hypervisors.kvm.storage.disk_dasd import DiskDasd
from tessia_baselib.hypervisors.kvm.storage.disk_fcp import DiskFcp
from time import sleep

import logging
import threading

#
# CONSTANTS AND DEFINTIONS
#
DISK_TYPEMAP = {
    "DASD": DiskDasd,
    "FCP": DiskFcp
}

MPATH_TEMPLATE = (r'''
defaults {
   default_features "1 queue_if_no_path"
   user_friendly_names no
   path_grouping_policy multibus
}

blacklist {
   devnode ".*"
}

blacklist_exceptions {
   devnode "^dasd[a-z]+[0-9]*"
   devnode "^sd[a-z]+[0-9]*"
}
''')

#
# CODE
#
class StoragePool(object):
    """
    This class represents a pool of disks to be handled
    """
    def __init__(self, disks, target_dev_mngr, host_conn):
        """
        Constructor
        """
        self._logger = logging.getLogger(__name__)
        self._target_dev_mngr = target_dev_mngr
        self._host_conn = host_conn

        self._mpath = False
        self._root = None
        self._disks = []
        for disk in disks:
            try:
                mpath = (disk['specs']['multipath'] is True)
            except KeyError:
                mpath = False
            self._mpath = (mpath is True) or self._mpath
            self._disks.append(self._create_disk(disk))

    # __init__()

    def _create_disk(self, parameters):
        """
        Factory function for disks

        Args:
            parameters (dict): Dictionary containing the definitions for
                               the specific disk type. A type property
                               must be provided in this dictionary.
        Returns:
            Disk: disk object instance

        Raises:
            RuntimeError: In case the type is not recognized.

        """
        try:
            disk_cls = DISK_TYPEMAP[parameters['type']]
        except KeyError:
            raise RuntimeError(
                "Unknown disk type {}".format(parameters['type']))

        return disk_cls(parameters, self._target_dev_mngr, self._host_conn)
    # _create_disk()

    def _mpath_start(self):
        """
        Apply multipath configuration and make sure daemon is running
        """
        shell = self._host_conn.open_session()
        shell.run('rm -f /etc/multipath.conf.bak && '
                  'cp /etc/multipath.conf /etc/multipath.conf.bak')
        cmd = "echo '%s' > /etc/multipath.conf" % MPATH_TEMPLATE
        ret, output = shell.run(cmd)
        if ret != 0:
            raise RuntimeError('Failed to create /etc/multipath.conf: %s'
                               % output.strip())

        ret, _ = shell.run(
            r"systemctl list-unit-files|grep -q '^ *multipathd\.service'")
        # multipathd is using systemd
        if ret == 0:
            cmd = ('systemctl restart multipathd.service && systemctl '
                   'status multipathd.service')
        # sysv
        else:
            cmd = '/etc/init.d/multipathd restart'
        ret, _ = shell.run(cmd)
        if ret != 0:
            raise RuntimeError('Failed to (re)start multipath daemon')

        shell.close()
    # _mpath_start()

    @staticmethod
    def _thread_wrap(ret, function, *args):
        """
        Wrapper to run a function as a thread and return possible exception

        Args:
            ret (list): shared list which will contain exception object
            function (function): function to be executed
            *args (list): arguments to function
        """
        try:
            function(*args)
        except Exception as exc:
            ret.append(exc)
    # _thread_wrap()

    def activate(self):
        """
        Activate all disks contained in the pool
        """
        # set multipath params and restart multipath
        if self._mpath:
            self._mpath_start()

        # disk activation threads
        tasks = {}
        for disk in self._disks:
            ret = []
            thread = threading.Thread(
                target=self._thread_wrap,
                args=(ret, disk.activate)
            )
            task = {'ret': ret, 'thread': thread}
            task['thread'].start()
            tasks[disk.volume_id] = task

        self._logger.info('Waiting for disk(s) activation')
        while True:
            # do not consume all cpu in an continuous loop, wait a while to
            # re-check threads
            sleep(0.5)
            for vol_id, task in list(tasks.items()):
                # task still running: wait
                if task['thread'].is_alive():
                    continue

                # task ended successfully: remove from map
                if not task['ret']:
                    tasks.pop(vol_id)
                    continue

                # disk activation failed, report error
                exc = task['ret'][0]
                raise RuntimeError(
                    'Failed to activate disk {}'.format(vol_id)) from exc

            # all tasks completed: end loop
            if not tasks:
                break
        self._logger.info('Disk(s) activation completed')
    # activate()

    def to_xml(self):
        """
        Return the libvirt xml definition of the disks contained in the pool
        """
        disks_xml = ""
        for disk in self._disks:
            disks_xml += disk.to_xml()

        return disks_xml
    # to_xml()

# StoragePool
