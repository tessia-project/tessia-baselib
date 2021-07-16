# Copyright 2021 IBM Corp.
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
Volume descriptor object representing DPM storage volume

Descriptors are data objects, containing filtered information about
storage configuration
"""

#
# IMPORTS
#
from zhmcclient import StorageVolume, Partition


#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#


def describe_storage_volume(volume: StorageVolume, partition: Partition):
    """
    Create VolumeDescriptor instance from DPM information
    """
    desc = {
        'uri': volume.uri,
        # a volume might not be ready yet - this is indicated by
        # fulfillment state. HPAV aliases have null here
        'is_fulfilled': volume.get_property('fulfillment-state') in [
            'complete', 'overprovisioned'
        ],
        'size': volume.prop('active-size', 0.),
        'attachment': volume.manager.storage_group.get_property(
            'type'),
    }

    if desc['attachment'] == 'fc':
        # ECKD volume
        desc.update({
            'device_nr': volume.get_property('device-number'),
            'is_alias': volume.get_property('eckd-type') == 'alias'
        })
        return FiconVolumeDescriptor(**desc)

    if desc['attachment'] == 'fcp':
        # SCSI on FCP
        desc.update({
            'uuid': volume.get_property('uuid'),
        })
        # from all paths available to a volume
        # pick only those for current partition
        desc['paths'] = [
            {
                'device_nr': path['device-number'],
                'wwpn': path['target-world-wide-port-name'],
                'lun': path['logical-unit-number']
            } for path in (volume.prop('paths') or [])
            if path['partition-uri'] == partition.uri
        ]
        return FcpVolumeDescriptor(**desc)

    # otherwise return a generic descriptor
    return VolumeDescriptor(**desc)


class VolumeDescriptor:
    """
    Generic descriptor for DPM storage volume attached to a partition
    """

    def __init__(self, uri: str, is_fulfilled: bool, size: float,
                 attachment: str) -> None:
        """
        Initialize a generic volume descriptor
        """
        self.uri = uri
        self.is_fulfilled = is_fulfilled
        self.size = size
        self.attachment = attachment
    # __init__()

    def __str__(self):
        """
        String representation of the descriptor
        """
        return "VolumeDescriptor<{}>".format(self.uri)
    # __str__()

# VolumeDescriptor


class FiconVolumeDescriptor(VolumeDescriptor):
    """
    Descriptor for FICON-attached volumes
    """

    def __init__(self, device_nr: str, is_alias: bool, **kwargs) -> None:
        """
        Initialize FiconVolumeDescriptor instance
        """
        super().__init__(**kwargs)

        self.device_nr = device_nr
        self.is_alias = is_alias
    # __init__()

    def __str__(self):
        """
        String representation of the descriptor
        """
        return "FiconVolumeDescriptor<{}, devno={}>".format(
            self.uri, self.device_nr)
    # __str__()

# FiconVolumeDescrtiptor


class FcpVolumeDescriptor(VolumeDescriptor):
    """
    Descriptor for FCP-attached volumes
    """

    def __init__(self, uuid: str, paths: list, **kwargs) -> None:
        """
        Initialize FcpVolumeDescriptor instance
        """
        super().__init__(**kwargs)

        self.uuid = uuid
        self.paths = paths
    # __init__()

    def __str__(self):
        """
        String representation of the descriptor
        """
        return "FcpVolumeDescrtiptor<{}, uuid={}>".format(self.uri, self.uuid)
    # __str__()

# FcpVolumeDescrtiptor
