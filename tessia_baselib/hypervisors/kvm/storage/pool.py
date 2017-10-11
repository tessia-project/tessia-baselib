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
from copy import deepcopy
from tessia_baselib.hypervisors.kvm.storage.disk import DiskBase

#
# CONSTANTS AND DEFINTIONS
#

#
# CODE
#
class StoragePool(object):
    """
    This class represents a pool of disks to be handled
    """
    def __init__(self, disks, hyp_dev_paths, target_dev_mngr):
        """
        Constructor

        Args:
            disks (list): list of dicts containing volume information
            hyp_dev_paths (dict): disk device paths on hypervisor keyed by
                                  volume_id
            target_dev_mngr (TargetDeviceManager): instance used to generate
                                                   devnos

        Raises:
            ValueError: in case a volume's device path is missing
        """
        self._disks = []
        # merge the hypervisor devpath information
        for disk in disks:
            disk_copy = deepcopy(disk)
            try:
                dev_path = hyp_dev_paths[disk_copy['volume_id']]
            except KeyError:
                raise ValueError('Missing device path on hypervisor for '
                                 'volume {}'.format(disk_copy['volume_id']))
            disk_copy['hyp_dev_path'] = dev_path
            self._disks.append(DiskBase(disk_copy, target_dev_mngr))
    # __init__()

    def to_xml(self):
        """
        Return the libvirt xml definition of the disks contained in the pool
        """
        disks_xml = ""
        for disk_obj in self._disks:
            disks_xml += disk_obj.to_xml()

        return disks_xml
    # to_xml()
# StoragePool
