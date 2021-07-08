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
Test module for the pool module.
"""

#
# IMPORTS
#
from copy import deepcopy
from tessia.baselib.hypervisors.kvm.storage import pool
from unittest import mock
from unittest import TestCase
from unittest.mock import patch

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
class TestStoragePool(TestCase):
    """
    Test the StoragePool class
    """
    @staticmethod
    def _disk_id_gen():
        """Helper generator"""
        counter = 0
        while True:
            yield counter
            counter += 1
    # _disk_id_gen()

    def setUp(self):
        """
        Set up the mocks common to the testcases
        """
        id_generate = self._disk_id_gen()
        patcher = patch.object(pool, 'DiskBase', autospec=True)
        self._mock_disk = patcher.start()
        self._mock_disk.side_effect = lambda a, b: mock.Mock(
            volume_id='disk{}'.format(next(id_generate)))

        self.addCleanup(patcher.stop)

        # Target manager
        self._mock_tgt_mngr = mock.Mock()

        # create an instance for convenient usage
        self._volumes = [
            {
                'type': 'DASD',
                'volume_id': '09ab'
            },
            {
                'type': 'FCP',
                'volume_id': '4000000000000002220'
            },
        ]
        # simulate hypervisor dev paths
        self._dev_paths = {
            '09ab': '/dev/disk/by-path/ccw-0.0.09ab',
            '4000000000000002220': '/dev/mapper/3600000000033'
        }
        self._pool_obj = pool.StoragePool(
            self._volumes, self._dev_paths, self._mock_tgt_mngr)
    # setUp()

    def test_init(self):
        """
        Exercise the constructor
        """
        # add the expected devpath for verification
        check_vols = []
        for check_vol in deepcopy(self._volumes):
            check_vol['hyp_dev_path'] = self._dev_paths[check_vol['volume_id']]
            check_vols.append(check_vol)

        # verify that correct disks were created
        self._mock_disk.assert_has_calls([
            mock.call(check_vols[0], self._mock_tgt_mngr),
            mock.call(check_vols[1], self._mock_tgt_mngr)
        ])
        self.assertEqual(len(self._pool_obj._disks), 2)
    # test_init()

    def test_init_invalid_input(self):
        """
        Exercise the scenario where the a device path is missing for a volume.
        """
        msg = 'Missing device path on hypervisor for volume 09ab'
        with self.assertRaisesRegex(ValueError, msg):
            self._pool_obj = pool.StoragePool(
                self._volumes, {}, self._mock_tgt_mngr)

    # test_init_invalid_input()

    def test_to_xml(self):
        """
        Exercise collecting the xml representation of each disk
        """
        expected_xml = ''
        for i, disk in enumerate(self._pool_obj._disks):
            disk.to_xml.return_value = 'disk_xml{}'.format(i)
            expected_xml += disk.to_xml.return_value

        self.assertEqual(self._pool_obj.to_xml(), expected_xml)
# TestStoragePool
