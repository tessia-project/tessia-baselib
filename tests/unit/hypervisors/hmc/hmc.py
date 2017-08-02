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
Testing class for the HMC hypervisor
"""

#
# IMPORTS
#
from collections import OrderedDict
from tessia_baselib.hypervisors.hmc import hmc
from tessia_baselib.hypervisors.hmc.zhmc.exceptions import ZHmcError
from unittest import mock
from unittest import TestCase
from unittest.mock import patch

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
class TestHypervisorHmc(TestCase):
    """
    Unit test for the HypervisorHmc class
    """
    def setUp(self):
        """
        Setup a HypervisorHmc object and related mocks.
        """
        self.system_name = 'dummy_system'
        self.host_name = 'dummy.domain.com'
        self.user = 'root'
        self.passwd = 'somepwd'
        self.parameters = {}

        # mock the ZHmc class
        self._patcher_zhmc = patch.object(hmc, 'ZHmc')
        self._mock_zhmc = self._patcher_zhmc.start()
        self.addCleanup(self._patcher_zhmc.stop)

        # subprocess used to ping target system
        self._patcher_subprocess = patch.object(hmc, 'subprocess')
        self._mock_subprocess = self._patcher_subprocess.start()
        self.addCleanup(self._patcher_subprocess.stop)

        # mock the logger returned by get_logger
        self._patcher_logger = patch.object(hmc, 'get_logger')
        self._mock_get_logger = self._patcher_logger.start()
        self.addCleanup(self._patcher_logger.stop)
        self._mock_logger = mock.Mock(
            spec=['info', 'warning', 'error', 'debug'])
        self._mock_get_logger.return_value = self._mock_logger

        # mock the time functions to skip waiting for sleeps
        self._patcher_time = patch.object(hmc, 'time', autospec=True)
        self._mock_time = self._patcher_time.start()
        self.addCleanup(self._patcher_time.stop)
        def time_generator():
            """Generator for increasing time counter"""
            start = 1.1
            while True:
                start += 1.111
                yield start
        get_time = time_generator()
        self._mock_time.time.side_effect = lambda: next(get_time)

        # instantiate the object to be used in the testcases
        self.hmc_object = hmc.HypervisorHmc(
            self.system_name,
            self.host_name,
            self.user,
            self.passwd,
            self.parameters
        )
    # setUp()

    def test_attributes(self):
        """
        Validate if attributes were correctly assigned to object

        Raises:
            AssertionError: if validation fails
        """
        self.assertEqual('hmc', self.hmc_object.HYP_ID)
        self.assertEqual(self.system_name, self.hmc_object.name)
        self.assertEqual(self.host_name, self.hmc_object.host_name)
        self.assertEqual(self.user, self.hmc_object.user)
        self.assertEqual(self.passwd, self.hmc_object.passwd)
        self.assertEqual(self.parameters, self.hmc_object.parameters)
    # test_attributes()

    def test_login(self):
        """
        Check if the login() method works as expected

        Args:
            None

        Raises:
            AssertionError: if validation fails
        """
        # regular scenario
        self.hmc_object.login()
        self.assertIs(self.hmc_object._session, self._mock_zhmc.return_value)

        # test login on already active connection
        self.hmc_object.login()
        self._mock_logger.warning.assert_called_with(
            "Login called with connection already active:"
            " dropping previous connection object"
        )
    # test_login()

    def test_logoff(self):
        """
        Check if the logoff() method works as expected

        Args:
            None

        Raises:
            AssertionError: if validation fails
        """
        # check if exception is raised on logoff performed without previous
        # login
        with self.assertRaises(ZHmcError):
            self.hmc_object.logoff()

        # set the return value so the logoff can properly work
        session = self._mock_zhmc.return_value.session = mock.Mock()
        session.close_session.return_value = "foo"

        # regular scenario
        self.hmc_object.login()
        self.hmc_object.logoff()

        # check if session was really reset
        self.assertIs(self.hmc_object._session, None)
    # test_logoff()

    def test_start(self):
        """
        Check if the start() method works as expected

        Args:
            None

        Raises:
            AssertionError: if validation fails
        """
        # setting up the mock objects
        mock_lpar = (
            self._mock_zhmc.return_value.get_cpc.return_value.
            get_lpar.return_value
        )
        mock_image_profile = (
            self._mock_zhmc.return_value.get_cpc.return_value.
            get_image_profile.return_value
        )
        mock_image_profile.get_properties.return_value = {
            'central-storage': 4096,
            'number-shared-general-purpose-processors': 5,
            'number-shared-ifl-processors': 1
        }

        # check if exception is raised on start performed without previous
        # login
        parameters = {
            'cpc_name': 'dummy',
            'boot_params': {
                "boot_method": "dasd",
                "devicenr": "9999"
            }
        }
        with self.assertRaises(ZHmcError):
            self.hmc_object.start('dummy', 'dummy', 'dummy', parameters)

        # regular scenario
        self.hmc_object.login()

        # perform the operation when the image profile needs to update cpu
        # and memory using a DASD disk
        lpar_name = 'dummy_lpar'
        cpu = 10
        memory = 1024
        parameters = {
            'cpc_name': 'my_cpc',
            'boot_params': {
                'boot_method': 'dasd',
                'devicenr': '9999'
            }
        }

        self.hmc_object.start(lpar_name, cpu, memory, parameters)
        mock_lpar.activate.assert_called_with()
        mock_lpar.load.assert_called_with('9999')

        # test in case of operation error
        mock_lpar.load.side_effect = ZHmcError('Error')
        self.hmc_object._logger = mock.create_autospec(
            self.hmc_object._logger
        )

        with self.assertRaises(ZHmcError):
            self.hmc_object.start(lpar_name, cpu, memory, parameters)
        # reset side effect
        mock_lpar.load.side_effect = mock.DEFAULT

        # perform the operation when the image profile do not need update
        # using a SCSI disk
        parameters = {
            'cpc_name': 'my_cpc',
            'boot_params': {
                'boot_method': 'scsi',
                'zfcp_devicenr':'1234',
                'wwpn': '4321',
                'lun': '1324'
            },
            'ifl_cpus': 1
        }

        cpu = 6
        memory = 4096
        mock_lpar.status = 'not-activated'
        self.hmc_object.start(lpar_name, cpu, memory, parameters)
        mock_lpar.activate.assert_called_with()
        mock_lpar.scsi_load.assert_called_with(
            '1234', '4321', '1324')
    # test_start()

    def test_stop(self):
        """
        Check if the stop() method works as expected

        Args:
            None

        Raises:
            AssertionError: if validation fails
        """
        mock_lpar = (
            self._mock_zhmc.return_value.get_cpc.return_value.
            get_lpar.return_value
        )
        mock_lpar.status = 'operating'

        # check if exception is raised on stop performed without previous
        # login
        with self.assertRaises(ZHmcError):
            self.hmc_object.stop('dummy', {'cpc_name': 'my_cpc'})

        # regular scenario
        self.hmc_object.login()
        self.hmc_object.stop('my_lpar', {'cpc_name': 'my_cpc'})
        mock_lpar.stop.assert_called_with()
        mock_lpar.reset_clear.assert_called_with()

        # test operation on invalid lpar status
        mock_lpar.status = 'dummy_status'
        with self.assertRaises(ZHmcError):
            self.hmc_object.stop('my_lpar', {'cpc_name': 'my_cpc'})
    # test_stop()

    def test_reboot(self):
        """
        Check if the reboot() method works as expected

        Args:
            None

        Raises:
            AssertionError: if validation fails
        """
        with self.assertRaises(NotImplementedError):
            self.hmc_object.reboot('dummy', {})
    # test_reboot()

    def test_netboot(self):
        """
        Check if the start() method works as expected when using
        network boot

        Args:
            None

        Raises:
            AssertionError: if validation fails
        """

        lpar_name = "dummy_lpar"
        cpu = 6
        memory = 4096

        parameters = {
            "cpc_name": "CP23",
            "boot_params": {
                "boot_method": "network",
                "cmdline": "some_url",
                "kernel_url": "some_url",
                "initrd_url": "some_url",
                "mac": "ff:ff:ff:ff:ff:ff",
                "ip": "9.9.9.9",
                "mask": "255.255.255.255",
                "gateway": "8.8.8.8",
                "device": "f500,f501,f502"
            }
        }

        # setting up the mock objects
        mock_lpar = (
            self._mock_zhmc.return_value.get_cpc.return_value.
            get_lpar.return_value
        )
        mock_image_profile = (
            self._mock_zhmc.return_value.get_cpc.return_value.
            get_image_profile.return_value
        )
        mock_image_profile.get_properties.return_value = {
            'central-storage': 4096,
            'number-shared-general-purpose-processors': 5,
            'number-shared-ifl-processors': 1
        }

        patcher_guest_linux = patch.object(hmc, 'GuestLinux')
        mock_guest_linux = patcher_guest_linux.start()

        # mock get_cpc to return the cpc name
        self._mock_zhmc.return_value.get_cpc.return_value.name = 'CP23'

        patcher_conf = patch.object(hmc, 'CONF')
        mock_conf = patcher_conf.start()
        self.addCleanup(patcher_conf.stop)
        mock_conf.get_config.return_value = {
            'netdisks': {'CP23': "FFFF"}
        }

        mock_lpar.get_properties.return_value = {
            'status': 'operating'
        }
        self.hmc_object.login()
        self.hmc_object.start(lpar_name, cpu, memory, parameters)

        # verify behavior
        mock_lpar.load.assert_called_with(
            'FFFF', timeout=hmc.NETBOOT_LOAD_TIMEOUT)

        boot_params = parameters.get('boot_params')

        ch_list = boot_params.get("device").split(",")
        # test network setup
        net_cmd_calls = [
            mock.call("root"),
            mock.call("somepasswd"),
            mock.call(
                "cio_ignore -r {} && \\".format(boot_params.get("device"))),
            mock.call(
                "znetconf -a {} -o layer2=1 && \\".format(ch_list[0])),
            mock.call("ifconfig enc{} hw ether {} && \\".format(
                ch_list[0], boot_params.get("mac"))),
            mock.call("ifconfig enc{} {} netmask {} && \\".format(
                ch_list[0], boot_params.get("ip"), boot_params.get("mask"))),
            mock.call("route add default gw {} && \\".format(
                boot_params.get("gateway"))),
            mock.call("ping -c 1 {}".format(boot_params.get('gateway')))
        ]
        mock_lpar.send_os_command.assert_has_calls(net_cmd_calls)

        # verify that we tried to reach target system
        self._mock_subprocess.run.assert_called_with(
            'ping -c 1 -w 5 ' + boot_params.get("ip"),
            shell=True, check=True,
            stdout=self._mock_subprocess.DEVNULL,
            stderr=self._mock_subprocess.DEVNULL)

        calls = [
            mock.call(boot_params.get("kernel_url"), "/tmp/kernel"),
            mock.call(boot_params.get("initrd_url"), "/tmp/initrd")
        ]

        mock_guest_linux.return_value.push_file.assert_has_calls(calls)

        session = mock_guest_linux.return_value.open_session.return_value
        session.run.assert_called_with(
            "killall -9 sshd; "
            "nohup kexec /tmp/kernel --initrd=/tmp/initrd --command-line='{}' "
            "&>/tmp/kexec.log".format(boot_params.get("cmdline")),
            ignore_ret=True
        )

        # test with a different channel format
        parameters["boot_params"]['device'] = "f500"
        mock_lpar.send_os_command.reset_mock()
        self.hmc_object.start(lpar_name, cpu, memory, parameters)
        f501 = hex(int("f500", 16)+1).strip("0x")
        f502 = hex(int("f500", 16)+2).strip("0x")
        # replace expected command
        net_cmd_calls[2] = mock.call(
            "cio_ignore -r {} && \\".format("f500," + f501 + "," +f502)
        )
        mock_lpar.send_os_command.has_calls(net_cmd_calls)

        # test with layer2 off and additional options
        # by using an ordered dict and placing layer2 on second position we
        # validate that layer2 always comes first
        parameters["boot_params"]['options'] = OrderedDict()
        parameters["boot_params"]['options']['portname'] = 'osaport'
        parameters["boot_params"]['options']['layer2'] = '0'
        parameters["boot_params"]['options']['portno'] = '0'
        parameters["boot_params"]['options']['buffer_count'] = '128'
        mock_lpar.send_os_command.reset_mock()
        self.hmc_object.start(lpar_name, cpu, memory, parameters)
        # replace expected commands
        net_cmd_calls[3] = mock.call(
            "znetconf -a {} -o layer2=0 -o portname=osaport -o portno=0 "
            "-o buffer_count=128 && \\".format(ch_list[0])
        )
        # mac address is not set when layer2 is off
        net_cmd_calls.pop(4)
        mock_lpar.send_os_command.assert_has_calls(net_cmd_calls)

    # test_netboot()

    def test_netboot_no_disk(self):
        """
        Exercise the scenario where there is no auxiliary disk for the given
        cpc.
        """
        cpc_name = 'YY22'
        lpar_name = "dummy_lpar"
        cpu = 6
        memory = 4096

        parameters = {
            "cpc_name": cpc_name,
            "boot_params": {
                "boot_method": "network",
                "cmdline": "some_url",
                "kernel_url": "some_url",
                "initrd_url": "some_url",
                "mac": "ff:ff:ff:ff:ff:ff",
                "ip": "9.9.9.9",
                "mask": "255.255.255.255",
                "gateway": "8.8.8.8",
                "device": "f500,f501,f502"
            }
        }

        # mock get_cpc to return the cpc name
        self._mock_zhmc.return_value.get_cpc.return_value.name = cpc_name

        # mock configuration file
        patcher_conf = patch.object(hmc, 'CONF')
        mock_conf = patcher_conf.start()
        self.addCleanup(patcher_conf.stop)
        mock_conf.get_config.return_value = {
            'netdisks': {'XX11': "FFFF"}
        }

        self.hmc_object.login()
        with self.assertRaisesRegex(
            ZHmcError,
            'Operation failed with: No auxiliary disk configured for '
            'CPC {}'.format(cpc_name)):
            self.hmc_object.start(lpar_name, cpu, memory, parameters)

    # test_netboot_no_disk()

    def test_netboot_load_timeout(self):
        """
        Check if the start() method works as expected when using
        network boot and a timeout happens during load

        Args:
            None

        Raises:
            AssertionError: if validation fails
        """
        lpar_name = "dummy_lpar"
        cpu = 6
        memory = 4096

        parameters = {
            "cpc_name": "CP23",
            "boot_params": {
                "boot_method": "network",
                "cmdline": "some_url",
                "kernel_url": "some_url",
                "initrd_url": "some_url",
                "mac": "ff:ff:ff:ff:ff:ff",
                "ip": "9.9.9.9",
                "mask": "255.255.255.255",
                "gateway": "8.8.8.8",
                "device": "f500,f501,f502"
            }
        }

        # mock get_cpc to return the cpc name
        self._mock_zhmc.return_value.get_cpc.return_value.name = 'CP23'

        mock_image_profile = (
            self._mock_zhmc.return_value.get_cpc.return_value.
            get_image_profile.return_value
        )
        mock_image_profile.get_properties.return_value = {
            'central-storage': 4096,
            'number-shared-general-purpose-processors': 5,
            'number-shared-ifl-processors': 1
        }

        patcher_conf = patch.object(hmc, 'CONF')
        mock_conf = patcher_conf.start()
        self.addCleanup(patcher_conf.stop)
        mock_conf.get_config.return_value = {
            'netdisks': {'CP23': "FFFF"}
        }

        self.hmc_object.login()
        with self.assertRaisesRegex(
            ZHmcError,
            'Operation failed with: Timed out while performing load of '
            'auxiliary system'):
            self.hmc_object.start(lpar_name, cpu, memory, parameters)
    # test_netboot_load_timeout()

    def test_netboot_network_timeout(self):
        """
        Check if the start() method works as expected when using
        network boot and a timeout happens during setting up network on
        auxiliary system

        Args:
            None

        Raises:
            AssertionError: if validation fails
        """
        lpar_name = "dummy_lpar"
        cpu = 6
        memory = 4096

        parameters = {
            "cpc_name": "CP23",
            "boot_params": {
                "boot_method": "network",
                "cmdline": "some_url",
                "kernel_url": "some_url",
                "initrd_url": "some_url",
                "mac": "ff:ff:ff:ff:ff:ff",
                "ip": "9.9.9.9",
                "mask": "255.255.255.255",
                "gateway": "8.8.8.8",
                "device": "f500,f501,f502"
            }
        }

        # mock get_cpc to return the cpc name
        self._mock_zhmc.return_value.get_cpc.return_value.name = 'CP23'

        mock_image_profile = (
            self._mock_zhmc.return_value.get_cpc.return_value.
            get_image_profile.return_value
        )
        mock_image_profile.get_properties.return_value = {
            'central-storage': 4096,
            'number-shared-general-purpose-processors': 5,
            'number-shared-ifl-processors': 1
        }

        patcher_conf = patch.object(hmc, 'CONF')
        mock_conf = patcher_conf.start()
        self.addCleanup(patcher_conf.stop)
        mock_conf.get_config.return_value = {
            'netdisks': {'CP23': "FFFF"}
        }
        # set the mock so that the load operation works
        mock_lpar = (
            self._mock_zhmc.return_value.get_cpc.return_value.
            get_lpar.return_value
        )
        mock_lpar.get_properties.return_value = {
            'status': 'operating'
        }
        # set the subprocess mock so that the network configuration fails
        self._mock_subprocess.CalledProcessError = Exception
        self._mock_subprocess.run.side_effect = Exception()

        self.hmc_object.login()
        with self.assertRaisesRegex(
            ZHmcError,
            'Operation failed with: Timed out while waiting for network on '
            'auxiliary system'):
            self.hmc_object.start(lpar_name, cpu, memory, parameters)
    # test_netboot_network_timeout()

# TestHypervisorHmc
