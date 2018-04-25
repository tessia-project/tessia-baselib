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
from tessia.baselib.hypervisors.hmc import hmc
from tessia.baselib.hypervisors.hmc.zhmc.exceptions import ZHmcError
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
        self.user = 'HMCUSER'
        self.passwd = 'somepwd'
        self.parameters = {}

        # mock the ZHmc class
        patcher_zhmc = patch.object(hmc, 'ZHmc')
        self._mock_zhmc_cls = patcher_zhmc.start()
        self._mock_zhmc_obj = self._mock_zhmc_cls.return_value
        self.addCleanup(patcher_zhmc.stop)

        # useful references to mock objects
        self._mock_cpc = self._mock_zhmc_obj.get_cpc.return_value
        self._mock_lpar = self._mock_cpc.get_lpar.return_value

        # subprocess used to ping target system
        patcher_subprocess = patch.object(hmc, 'subprocess')
        self._mock_subprocess = patcher_subprocess.start()
        self.addCleanup(patcher_subprocess.stop)

        # guestlinux used when performing kexec
        patcher_guest_linux = patch.object(hmc, 'GuestLinux')
        self._mock_guest_linux = patcher_guest_linux.start()
        self.addCleanup(patcher_guest_linux.stop)

        # mock the logger returned by get_logger
        patcher_logger = patch.object(hmc, 'get_logger')
        self._mock_get_logger = patcher_logger.start()
        self.addCleanup(patcher_logger.stop)
        self._mock_logger = mock.Mock(
            spec=['info', 'warning', 'error', 'debug'])
        self._mock_get_logger.return_value = self._mock_logger

        # mock the time functions to skip waiting for sleeps
        patcher_time = patch.object(hmc, 'time', autospec=True)
        self._mock_time = patcher_time.start()
        self.addCleanup(patcher_time.stop)
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

    def _assert_net_boot(self, net_boot):
        """
        Assert that the netboot occurred as expected.

        Args:
            net_boot (dict): boot parameters used containing kernel info
        """
        calls = [
            mock.call(net_boot.get("kernel_url"), "/tmp/kernel"),
            mock.call(net_boot.get("initrd_url"), "/tmp/initrd")
        ]

        self._mock_guest_linux.return_value.push_file.assert_has_calls(calls)

        session = self._mock_guest_linux.return_value.open_session.return_value
        session.run.assert_called_with(
            "killall -9 sshd; "
            "nohup kexec /tmp/kernel --initrd=/tmp/initrd --command-line='{}' "
            "&>/tmp/kexec.log".format(net_boot["cmdline"]),
            ignore_ret=True
        )
    # _assert_net_boot()

    def _assert_net_setup(self, net_setup):
        """
        Assert that network setup was properly done.

        Args:
            net_setup (dict): network parameters used
        """
        ch_list = net_setup.get("device").split(",")
        if len(ch_list) > 1:
            cio_expected = net_setup.get("device")
        else:
            chan_2 = hex(int(net_setup.get("device"), 16)+1).strip("0x")
            chan_3 = hex(int(net_setup.get("device"), 16)+2).strip("0x")
            cio_expected = '{},{},{}'.format(
                net_setup.get("device"), chan_2, chan_3)

        znet_expected = 'znetconf -a {}'.format(ch_list[0])
        options = net_setup.get('options')
        if not options or not options.get('layer2'):
            znet_expected += ' -o layer2=0'
        else:
            for option, value in options.items():
                znet_expected += ' -o {}={}'.format(option, value)
        znet_expected += ' && \\'
        # build the list of expected calls
        net_cmd_calls = [
            mock.call("root"),
            mock.call(net_setup['password']),
            mock.call(
                "cio_ignore -r {} && \\".format(cio_expected)),
            mock.call(znet_expected),
        ]
        if ' layer2=1 ' in znet_expected and net_setup["mac"]:
            net_cmd_calls.append(
                mock.call("ifconfig enc{} hw ether {} && \\".format(
                    ch_list[0], net_setup["mac"]))
            )
        net_cmd_calls.extend([
            mock.call("ifconfig enc{} {} netmask {} && \\".format(
                ch_list[0], net_setup.get("ip"), net_setup.get("mask"))),
            mock.call("route add default gw {} && \\".format(
                net_setup.get("gateway"))),
        ])
        dns_servers = net_setup.get('dns')
        if dns_servers:
            net_cmd_calls.append(mock.call("echo > /etc/resolv.conf && \\"))
            for dns_entry in dns_servers:
                net_cmd_calls.append(
                    mock.call("echo 'nameserver {}' >> /etc/resolv.conf && \\"
                              .format(dns_entry)))

        net_cmd_calls.append(
            mock.call("true; ping -c 1 {}".format(net_setup.get('gateway'))))
        self._mock_lpar.send_os_command.assert_has_calls(net_cmd_calls)

        # verify that we tried to reach target system
        self._mock_subprocess.run.assert_called_with(
            'ping -c 1 -w 5 ' + net_setup.get("ip"),
            shell=True, check=True,
            stdout=self._mock_subprocess.DEVNULL,
            stderr=self._mock_subprocess.DEVNULL)

    # _assert_net_setup()

    def test_attributes(self):
        """
        Validate if attributes were correctly assigned to object

        Raises:
            AssertionError: if validation fails
        """
        self.assertEqual('hmc', self.hmc_object.HYP_ID)
        self.assertEqual(self.system_name.upper(), self.hmc_object.name)
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
        self.assertIs(self.hmc_object._session, self._mock_zhmc_obj)

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
        session = self._mock_zhmc_obj.session = mock.Mock()
        session.close_session.return_value = "foo"

        # regular scenario
        self.hmc_object.login()
        self.hmc_object.logoff()

        # check if session was really reset
        self.assertIs(self.hmc_object._session, None)
    # test_logoff()

    def test_param_none(self):
        """
        Confirm that the constructor accepts also None as value for the
        'parameter' attribute and works correctly.
        """
        # setting up the mock objects
        self._mock_cpc.get_cpus.return_value = {'cpus_cp': 10, 'cpus_ifl': 10}
        mock_image_profile = self._mock_cpc.get_image_profile.return_value
        mock_image_profile.get_properties.return_value = {
            'central-storage': 4096,
            'number-shared-general-purpose-processors': 5,
            'number-shared-ifl-processors': 1
        }

        hmc_object = hmc.HypervisorHmc(
            self.system_name, self.host_name, self.user, self.passwd, None)
        hmc_object.login()

        lpar_name = 'dummy_lpar'
        cpu = 10
        memory = 1024
        parameters = {
            'boot_params': {
                'boot_method': 'dasd',
                'devicenr': '9999'
            }
        }
        hmc_object.start(lpar_name, cpu, memory, parameters)

        # validate
        self._mock_zhmc_obj.get_cpc.assert_called_with(
            self.system_name.upper())
        self._mock_cpc.get_lpar.assert_called_with(lpar_name.upper())
        self._mock_lpar.activate.assert_called_with()
        self._mock_lpar.load.assert_called_with('9999')
    # test_param_none()

    def test_start_dasd_update_profile(self):
        """
        Check if the start() method works as expected for a DASD based
        activation and update of the image profile. It also validates that the
        dynamic cpu allocation works correctly by assigning all available IFLs
        before assigning CPs.

        Args:
            None

        Raises:
            AssertionError: if validation fails
        """
        # setting up the mock objects
        self._mock_cpc.get_cpus.return_value = {'cpus_cp': 10, 'cpus_ifl': 10}
        mock_image_profile = self._mock_cpc.get_image_profile.return_value
        mock_image_profile.get_properties.return_value = {
            'central-storage': 4096,
            'number-shared-general-purpose-processors': 5,
            'number-shared-ifl-processors': 1
        }

        self.hmc_object.login()
        # perform the operation when the image profile needs to update cpu
        # and memory using a DASD disk
        lpar_name = 'dummy_lpar'
        cpu = 14
        memory = 1024
        parameters = {
            'boot_params': {
                'boot_method': 'dasd',
                'devicenr': '9999'
            }
        }
        self.hmc_object.start(lpar_name, cpu, memory, parameters)

        # validate
        self._mock_zhmc_obj.get_cpc.assert_called_with(
            self.system_name.upper())
        self._mock_cpc.get_lpar.assert_called_with(lpar_name.upper())
        self._mock_lpar.activate.assert_called_with()
        self._mock_lpar.load.assert_called_with('9999')
        # make sure no network config was attempted
        self._mock_lpar.send_os_command.assert_not_called()
        # validate that profile was correctly updated
        mock_image_profile.update.assert_called_with({
            'central-storage': 1024,
            'number-shared-general-purpose-processors': 4,
            'number-shared-ifl-processors': 10
        })
    # test_start_dasd_update_profile()

    def test_start_scsi_no_update(self):
        """
        Check if the start() method works as expected for a SCSI based
        activation and no update of the image profile. It also validates that
        the static cpu allocation works correctly by verifying that the
        calculated CPU numbers match the already assigned numbers in the
        activation profile leading to no update being necessary.

        """
        # perform the operation when the image profile do not need update
        # using a SCSI disk
        mock_profile = self._mock_cpc.get_image_profile.return_value
        mock_profile.get_properties.return_value = {
            'central-storage': 4096,
            'number-shared-general-purpose-processors': 6,
            'number-shared-ifl-processors': 1
        }

        lpar_name = 'dummy_lpar'
        parameters = {
            'boot_params': {
                'boot_method': 'scsi',
                'zfcp_devicenr':'1234',
                'wwpn': '4321',
                'lun': '1324'
            },
            'cpus_ifl': 1,
            'cpus_cp': 6,
        }
        cpu = 0
        memory = 4096
        self._mock_lpar.status = 'not-activated'
        self._mock_cpc.get_cpus.return_value = {'cpus_cp': 10, 'cpus_ifl': 10}

        self.hmc_object.login()
        self.hmc_object.start(lpar_name, cpu, memory, parameters)

        # validate
        self._mock_zhmc_obj.get_cpc.assert_called_with(
            self.system_name.upper())
        self._mock_cpc.get_lpar.assert_called_with(lpar_name.upper())
        self._mock_lpar.activate.assert_called_with()
        self._mock_lpar.scsi_load.assert_called_with(
            '1234', '4321', '1324')
        # make sure no network config was attempted
        self._mock_lpar.send_os_command.assert_not_called()
        # no update to activation profile
        mock_profile.update.assert_not_called()

    # test_start_scsi_no_update()

    def test_start_no_login(self):
        """
        Exercise the scenario where the start operation is called without a
        previous login.
        """
        # check if exception is raised on start performed without previous
        # login
        parameters = {
            'boot_params': {
                "boot_method": "dasd",
                "devicenr": "9999"
            }
        }
        with self.assertRaises(ZHmcError):
            self.hmc_object.start('dummy', 'dummy', 'dummy', parameters)
    # test_start_no_login()

    def test_start_operation_error(self):
        """
        Verify if the module correctly reports error when the load operation
        fails.
        """
        lpar_name = 'cpc1lp50'
        parameters = {
            'boot_params': {
                'boot_method': 'scsi',
                'zfcp_devicenr':'1234',
                'wwpn': '4321',
                'lun': '1324'
            },
            'cpus_ifl': 1
        }
        cpu = 6
        memory = 4096
        # test in case of operation error
        self._mock_lpar.load.side_effect = ZHmcError('Timeout')
        self.hmc_object._logger = mock.create_autospec(
            self.hmc_object._logger
        )

        with self.assertRaises(ZHmcError):
            self.hmc_object.start(lpar_name, cpu, memory, parameters)
    # test_start_operation_error()

    def test_start_netsetup(self):
        """
        Test start operation with auto network setup
        """
        # perform the operation when the image profile do not need update
        # using a SCSI disk
        lpar_name = 'dummy_lpar'
        parameters = {
            'boot_params': {
                'boot_method': 'scsi',
                'zfcp_devicenr':'1234',
                'wwpn': '4321',
                'lun': '1324',
                'netsetup': {
                    "mac": None,
                    "ip": "9.9.9.9",
                    "mask": "255.255.255.255",
                    "gateway": "8.8.8.8",
                    "device": "f500,f501,f502",
                    "password": "super_password",
                    "dns": ['9.9.9.25', '9.9.9.30']
                }
            },
            'cpus_ifl': 1
        }
        cpu = 6
        memory = 4096
        self._mock_lpar.status = 'not-activated'
        self._mock_lpar.get_properties.return_value = {
            'status': 'operating'
        }
        self._mock_cpc.get_cpus.return_value = {'cpus_cp': 10, 'cpus_ifl': 10}

        self.hmc_object.login()
        self.hmc_object.start(lpar_name, cpu, memory, parameters)

        # validate
        self._mock_zhmc_obj.get_cpc.assert_called_with(
            self.system_name.upper())
        self._mock_cpc.get_lpar.assert_called_with(lpar_name.upper())
        self._mock_lpar.activate.assert_called_with()
        self._mock_lpar.scsi_load.assert_called_with(
            '1234', '4321', '1324')

        # validate network setup was executed
        self._assert_net_setup(parameters['boot_params']['netsetup'])

        # validate netboot was not performed
        self._mock_guest_linux.return_value.open_session.assert_not_called()
    # test_start_netsetup()

    def test_start_netsetup_netboot(self):
        """
        Test variation of start operation with netsetup and netboot
        """
        lpar_name = 'dummy_lpar'
        parameters = {
            'boot_params': {
                'boot_method': 'dasd',
                'devicenr': '9999',
                'netsetup': {
                    "mac": "ff:ff:ff:ff:ff:ff",
                    "ip": "9.9.9.9",
                    "mask": "255.255.255.255",
                    "gateway": "8.8.8.8",
                    "device": "f500,f501,f502",
                    "password": "super_password",
                },
                'netboot': {
                    "cmdline": "some_cmdline",
                    "kernel_url": "some_url",
                    "initrd_url": "some_url",
                }
            },
            'cpus_ifl': 1
        }
        cpu = 6
        memory = 4096
        self._mock_lpar.status = 'not-activated'
        self._mock_lpar.get_properties.return_value = {
            'status': 'operating'
        }
        self._mock_cpc.get_cpus.return_value = {'cpus_cp': 10, 'cpus_ifl': 10}

        self.hmc_object.login()
        self.hmc_object.start(lpar_name, cpu, memory, parameters)

        # validate
        self._mock_zhmc_obj.get_cpc.assert_called_with(
            self.system_name.upper())
        self._mock_cpc.get_lpar.assert_called_with(lpar_name.upper())
        self._mock_lpar.activate.assert_called_with()
        self._mock_lpar.load.assert_called_with(
            parameters['boot_params']['devicenr'])

        # validate network setup was executed
        self._assert_net_setup(parameters['boot_params']['netsetup'])

        # validate netboot occurred
        self._assert_net_boot(parameters['boot_params']['netboot'])
    # test_start_netsetup_netboot()

    def test_stop(self):
        """
        Check if the stop() method works as expected

        Args:
            None

        Raises:
            AssertionError: if validation fails
        """
        lpar_name = 'my_lpar'
        self._mock_lpar.status = 'operating'

        # check if exception is raised on stop performed without previous
        # login
        with self.assertRaises(ZHmcError):
            self.hmc_object.stop('dummy', {})

        # regular scenario
        self.hmc_object.login()
        self.hmc_object.stop('my_lpar', {})
        # names in hmc in classic mode are always uppercased, check if we made
        # the call in uppercase
        self._mock_zhmc_obj.get_cpc.assert_called_with(
            self.system_name.upper())
        self._mock_cpc.get_lpar.assert_called_with(lpar_name.upper())
        self._mock_lpar.stop.assert_called_with()
        self._mock_lpar.reset_clear.assert_called_with()

    def test_stop_invalid_status(self):
        """
        Check if the stop() also works even if the lpar is not in operating
        state.
        """
        # test operation on invalid lpar status - should work anyway, the
        # hmc api just ignores it
        lpar_name = 'my_lpar'
        self._mock_lpar.status = 'not-operating'
        self.hmc_object.login()
        self.hmc_object.stop(lpar_name, {})

        # validate
        self._mock_zhmc_obj.get_cpc.assert_called_with(
            self.system_name.upper())
        self._mock_cpc.get_lpar.assert_called_with(lpar_name.upper())
        self._mock_lpar.stop.assert_called_with()
        self._mock_lpar.reset_clear.assert_called_with()
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

    def test_start_netboot_additional(self):
        """
        Check if the start() method works as expected when using network
        boot with additional options

        Args:
            None

        Raises:
            AssertionError: if validation fails
        """
        lpar_name = "dummy_lpar"
        cpu = 6
        memory = 4096

        parameters = {
            "boot_params": {
                "boot_method": "dasd",
                'devicenr': 'FFFF',
                'netsetup': {
                    "mac": "ff:ff:ff:ff:ff:ff",
                    "ip": "9.9.9.9",
                    "mask": "255.255.255.255",
                    "gateway": "8.8.8.8",
                    # test with a different channel format
                    "device": "f500",
                    "password": "somepwd",
                },
                'netboot': {
                    "cmdline": "some_cmdline",
                    "kernel_url": "some_url",
                    "initrd_url": "some_url",
                }
            }
        }

        # setting up the mock objects
        mock_image_profile = self._mock_cpc.get_image_profile.return_value
        mock_image_profile.get_properties.return_value = {
            'central-storage': 4096,
            'number-shared-general-purpose-processors': 5,
            'number-shared-ifl-processors': 1
        }

        self._mock_lpar.get_properties.return_value = {
            'status': 'operating'
        }
        self._mock_cpc.get_cpus.return_value = {'cpus_cp': 10, 'cpus_ifl': 10}

        self.hmc_object.login()
        self.hmc_object.start(lpar_name, cpu, memory, parameters)
        net_setup = parameters['boot_params']['netsetup']
        self._assert_net_setup(net_setup)

        # test with layer2 on and additional options
        # by using an ordered dict and placing layer2 on second position we
        # validate that layer2 always comes first
        net_setup['options'] = OrderedDict()
        net_setup['options']['layer2'] = '1'
        net_setup['options']['portname'] = 'osaport'
        net_setup['options']['portno'] = '0'
        net_setup['options']['buffer_count'] = '128'
        self._mock_lpar.send_os_command.reset_mock()
        self.hmc_object.start(lpar_name, cpu, memory, parameters)
        self._assert_net_setup(net_setup)

    # test_start_netboot_additional()

    def test_start_netboot_layer2_no_mac(self):
        """
        Test the scenario where layer2 is on but no mac address is specified.
        """
        lpar_name = "dummy_lpar"
        cpu = 6
        memory = 4096

        parameters = {
            "boot_params": {
                "boot_method": "dasd",
                'devicenr': 'FFFF',
                'netsetup': {
                    "mac": None,
                    "ip": "9.9.9.9",
                    "mask": "255.255.255.255",
                    "gateway": "8.8.8.8",
                    # test with a different channel format
                    "device": "f500",
                    "password": "somepwd",
                },
                'netboot': {
                    "cmdline": "some_cmdline",
                    "kernel_url": "some_url",
                    "initrd_url": "some_url",
                }
            }
        }

        # setting up the mock objects
        mock_image_profile = self._mock_cpc.get_image_profile.return_value
        mock_image_profile.get_properties.return_value = {
            'central-storage': 4096,
            'number-shared-general-purpose-processors': 5,
            'number-shared-ifl-processors': 1
        }

        self._mock_lpar.get_properties.return_value = {
            'status': 'operating'
        }
        self._mock_cpc.get_cpus.return_value = {'cpus_cp': 10, 'cpus_ifl': 10}

        # by using an ordered dict and placing layer2 on second position we
        # validate that layer2 always comes first
        net_setup = parameters['boot_params']['netsetup']
        net_setup['options'] = OrderedDict()
        net_setup['options']['layer2'] = '1'
        net_setup['options']['portname'] = 'osaport'
        net_setup['options']['portno'] = '0'
        net_setup['options']['buffer_count'] = '128'
        self.hmc_object.login()
        self.hmc_object.start(lpar_name, cpu, memory, parameters)
        self._assert_net_setup(net_setup)
    # test_start_netboot_layer2_no_mac()

    def test_start_netboot_load_timeout(self):
        """
        Check if the start() method works as expected when using
        network boot and a timeout happens during load

        Args:
            None

        Raises:
            AssertionError: if validation fails
        """
        # instantiate an object to use a different cpc name
        cpc_name = 'CP23'
        hmc_object = hmc.HypervisorHmc(
            cpc_name, self.host_name, self.user, self.passwd, self.parameters)
        # mock get_cpc to return the cpc name
        self._mock_zhmc_obj.get_cpc.return_value.name = cpc_name
        # mock image profile
        mock_image_profile = self._mock_cpc.get_image_profile.return_value
        mock_image_profile.get_properties.return_value = {
            'central-storage': 4096,
            'number-shared-general-purpose-processors': 5,
            'number-shared-ifl-processors': 1
        }

        # perform call and validate error
        lpar_name = "dummy_lpar"
        cpu = 6
        memory = 4096
        parameters = {
            "boot_params": {
                'boot_method': 'dasd',
                'devicenr': '9999',
                'netsetup': {
                    "mac": "ff:ff:ff:ff:ff:ff",
                    "ip": "9.9.9.9",
                    "mask": "255.255.255.255",
                    "gateway": "8.8.8.8",
                    "device": "f500,f501,f502",
                    "password": "somepwd",
                },
                'netboot': {
                    "cmdline": "some_cmdline",
                    "kernel_url": "some_url",
                    "initrd_url": "some_url",
                }
            }
        }
        self._mock_cpc.get_cpus.return_value = {'cpus_cp': 10, 'cpus_ifl': 10}

        hmc_object.login()
        with self.assertRaisesRegex(
            ZHmcError,
            'Operation failed with: Timed out while waiting for load of '
            'operating system'):
            hmc_object.start(lpar_name, cpu, memory, parameters)
    # test_start_netboot_load_timeout()

    def test_start_netboot_network_timeout(self):
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
            "boot_params": {
                'boot_method': 'scsi',
                'zfcp_devicenr':'1234',
                'wwpn': '4321',
                'lun': '1324',
                'netsetup': {
                    "mac": "ff:ff:ff:ff:ff:ff",
                    "ip": "9.9.9.9",
                    "mask": "255.255.255.255",
                    "gateway": "8.8.8.8",
                    "device": "f500,f501,f502",
                    "password": "super_password",
                    "dns": ['9.9.9.25', '9.9.9.30']
                },
                'netboot': {
                    "cmdline": "some_cmdline",
                    "kernel_url": "some_url",
                    "initrd_url": "some_url",
                }
            }
        }

        # mock get_cpc to return the cpc name
        self._mock_cpc.name = self.system_name.upper()
        # image profile values
        mock_image_profile = self._mock_cpc.get_image_profile.return_value
        mock_image_profile.get_properties.return_value = {
            'central-storage': 4096,
            'number-shared-general-purpose-processors': 5,
            'number-shared-ifl-processors': 1
        }
        # set the mock so that the load operation works
        self._mock_lpar.get_properties.return_value = {'status': 'operating'}
        # set the subprocess mock so that the network configuration fails
        self._mock_subprocess.CalledProcessError = Exception
        self._mock_subprocess.run.side_effect = Exception()
        self._mock_cpc.get_cpus.return_value = {'cpus_cp': 10, 'cpus_ifl': 10}

        self.hmc_object.login()
        with self.assertRaisesRegex(
            ZHmcError,
            'Operation failed with: Timed out while waiting for network on '
            'loaded operating system'):
            self.hmc_object.start(lpar_name, cpu, memory, parameters)
    # test_start_netboot_network_timeout()

    def test_cpu_dynamic_not_enough(self):
        """
        Check if the dynamic strategy correctly reports error when the
        requested number of generic CPUs exceed the quantity available in the
        CPC.
        """
        # setting up the mock objects
        avail = {'cpus_cp': 2, 'cpus_ifl': 2}
        self._mock_cpc.get_cpus.return_value = avail

        hmc_object = hmc.HypervisorHmc(
            self.system_name, self.host_name, self.user, self.passwd, None)

        lpar_name = 'dummy_lpar'
        cpu = 5
        memory = 1024
        parameters = {
            'boot_params': {
                'boot_method': 'dasd',
                'devicenr': '9999'
            }
        }
        hmc_object.login()
        error_msg = (
            'Not enough CPUs available in CPC. Requested: {} CPUs. '
            'Available: {} CPs, {} IFLs.'.format(
                cpu, avail['cpus_cp'], avail['cpus_ifl'])
        )
        with self.assertRaisesRegex(RuntimeError, error_msg):
            hmc_object.start(lpar_name, cpu, memory, parameters)
    # test_cpu_dynamic_not_enough()

    def test_cpu_static_not_enough(self):
        """
        Check if the static strategy correctly reports error when the
        requested number of defined-type CPUs exceed the quantity available in
        the CPC.
        """
        # setting up the mock objects
        avail = {'cpus_cp': 2, 'cpus_ifl': 2}
        self._mock_cpc.get_cpus.return_value = avail

        hmc_object = hmc.HypervisorHmc(
            self.system_name, self.host_name, self.user, self.passwd, None)

        lpar_name = 'dummy_lpar'
        cpu = 5
        memory = 1024
        parameters = {
            'boot_params': {
                'boot_method': 'dasd',
                'devicenr': '9999'
            },
            'cpus_cp': 2,
            'cpus_ifl': 10
        }
        hmc_object.login()
        error_msg = (
            'Not enough CPUs available in CPC. Requested: {} CPs, {} '
            'IFLs. Available: {} CPs, {} IFLs.'.format(
                parameters['cpus_cp'], parameters['cpus_ifl'],
                avail['cpus_cp'], avail['cpus_ifl'])
        )

        with self.assertRaisesRegex(RuntimeError, error_msg):
            hmc_object.start(lpar_name, cpu, memory, parameters)
    # test_cpu_static_not_enough()
# TestHypervisorHmc
