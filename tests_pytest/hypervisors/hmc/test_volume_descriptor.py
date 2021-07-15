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
Test Volume descriptor
"""

# pylint: disable=invalid-name  # we have really long test names

#
# IMPORTS
#
import zhmcclient_mock
from tessia.baselib.hypervisors.hmc.volume_descriptor import \
    describe_storage_volume, FiconVolumeDescriptor, FcpVolumeDescriptor
from zhmcclient_mock import FakedSession
from zhmcclient_mock._hmc import FakedStorageVolumeManager

import os
import pytest
import yaml


#
# CONSTANTS AND DEFINITIONS
#
DATA_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    './data')


def datafile(filename: str) -> str:
    """Return path to test data"""
    return os.path.join(DATA_DIR, filename)


@pytest.fixture(autouse=True)
def mock_get_property():
    """Automatically inmplement get_property"""

    def _get_property(self: zhmcclient_mock.FakedBaseResource, prop: str):
        return self._properties[prop]

    def _get_prop_or_default(self: zhmcclient_mock.FakedBaseResource,
                             prop: str, default=None):
        if not prop in self._properties:
            return default
        return self._properties[prop]

    zhmcclient_mock.FakedBaseResource.get_property = _get_property
    zhmcclient_mock.FakedBaseResource.prop = _get_prop_or_default


@pytest.fixture(autouse=True)
def mock_storage_volume_manager():
    """Mock missing methods in StorageVolumeManager"""

    @property
    def _get_storage_group(self: FakedStorageVolumeManager):
        return self._parent

    FakedStorageVolumeManager.storage_group = _get_storage_group


@pytest.fixture
def hmc_session():
    """Create a faked session with static data"""

    with open(datafile('hmcclient.yaml')) as hmcclient_file:
        client = yaml.safe_load(hmcclient_file).get('test_client')
    session_args = (
        client[key]
        for key in ['hmc_host', 'hmc_name', 'hmc_version', 'api_version'])
    session = FakedSession(*session_args)
    session.hmc.add_resources({
        'cpcs': client['cpcs'],
        'consoles': client['consoles']
    })

    yield session
    session.logoff()


def test_descriptor_from_ficon_is_correct(hmc_session: FakedSession):
    """Verify that volume descriptor for Ficon-attached disks is correct"""
    cpc = hmc_session.hmc.cpcs.list()[0]
    partition = cpc.partitions.list()[0]
    stgroup = hmc_session.hmc.consoles.list()[0].storage_groups.list(
        {'type': 'fc'})[0]
    dasd_volume = stgroup.storage_volumes.list({'eckd-type': 'base'})[0]
    alias_volume = stgroup.storage_volumes.list({'eckd-type': 'alias'})[0]

    dasd_descriptor = describe_storage_volume(dasd_volume, partition)
    alias_descriptor = describe_storage_volume(alias_volume, partition)

    # make sure we picked correct volume
    assert isinstance(dasd_descriptor, FiconVolumeDescriptor)
    assert not dasd_descriptor.is_alias
    assert isinstance(alias_descriptor, FiconVolumeDescriptor)
    assert alias_descriptor.is_alias


def test_descriptor_from_fcp_is_correct(hmc_session: FakedSession):
    """Verify that volume descriptor for FCP-attached disks is correct"""
    cpc = hmc_session.hmc.cpcs.list()[0]
    partition = cpc.partitions.list()[0]
    stgroup = hmc_session.hmc.consoles.list()[0].storage_groups.list(
        {'type': 'fcp'})[0]
    volume = stgroup.storage_volumes.list()[0]

    descriptor = describe_storage_volume(volume, partition)

    # make sure we picked correct volume
    assert volume.name == 'LU01'
    assert isinstance(descriptor, FcpVolumeDescriptor)
    assert descriptor.paths
