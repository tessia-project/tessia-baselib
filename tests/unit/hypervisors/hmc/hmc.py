# Copyright 2016, 2017, 2019 IBM Corp.
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
from unittest import mock
from unittest import TestCase
from unittest.mock import patch
from urllib.parse import urlsplit
from zhmcclient_mock import FakedSession, _hmc as zhmc_hmc, \
    _urihandler as zhmc_urihandler

import zhmcclient

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
class StorageVolumeHandler(zhmc_urihandler.GenericGetPropertiesHandler):
    """
    Add missing handler for storage volumes to zhmcclient_mock module
    """

class StorageVolumesHandler:
    """
    Add missing handler for storage groups to zhmcclient_mock module
    """
    # disable pylint to allow code to follow zhmcclient style
    # pylint: disable=all
    @staticmethod
    def get(method, hmc, uri, uri_parms, logon_required):
        """Operation: List Storage Volumes of a Storage Group"""
        sg_oid = uri_parms[0]
        query_str = uri_parms[1]
        filter_args = zhmc_urihandler.parse_query_parms(method, uri, query_str)
        try:
            sg_obj = (
                hmc.consoles.console.storage_groups.lookup_by_oid(sg_oid))
        except KeyError:
            raise zhmc_urihandler.InvalidResourceError(method, uri)
        result_storage_volumes = []
        for svol in sg_obj.storage_volumes.list(filter_args):
            result_storage_volumes.append(svol.properties)
        return {'storage-volumes': result_storage_volumes}
    # pylint: enable=all
# StorageVolumesHandler

# fix a bug with the base_uri for storage-volumes directly in the
# zhmmclient_mock module
def fixed_init(self, hmc, storage_group):
    super(zhmc_hmc.FakedStorageVolumeManager, self).__init__(
        hmc=hmc,
        parent=storage_group,
        resource_class=zhmc_hmc.FakedStorageVolume,
        base_uri=storage_group.uri + '/storage-volumes',
        oid_prop='element-id',
        uri_prop='element-uri',
        class_value='storage-volume')
zhmc_hmc.FakedStorageVolumeManager.__init__ = fixed_init

class MessagesChannelHandler(zhmc_urihandler.GenericGetPropertiesHandler):
    """
    Open messages channel
    """
    @staticmethod
    def post(method, hmc, uri, uri_parms, body, logon_required,
             wait_for_completion):
        """Operation: Open messages channel."""
        return {'topic-name': 'messages-topic'}

class MockFakedSession(FakedSession):
    """
    Wraps the FakedSession so that it behaves more like a real mock of the
    Session class.
    """
    def __init__(self, *args, **kwargs):
        if args:
            host_name = args[0]
        else:
            host_name = kwargs.get('host')
        valid_kwargs = {
            'host': host_name,
            'hmc_name': 'fake-hmc',
            'hmc_version': '2.13.1',
            'api_version': '1.8',
        }
        super().__init__(**valid_kwargs)

        # patch the list of uris to include scsi-load
        new_uris = tuple(
            list(zhmc_urihandler.URIS) +
            [(r'/api/logical-partitions/([^/]+)/operations/scsi-load',
              zhmc_urihandler.LparLoadHandler),
             (r'/api/storage-groups/([^/]+)/storage-volumes(?:\?(.*))?',
              StorageVolumesHandler),
             (r'/api/storage-groups/([^/]+)/storage-volumes/([^/]+)',
              StorageVolumeHandler),
             (r'/api/partitions/([^/]+)/operations/open-os-message-channel',
              MessagesChannelHandler),
             (r'/api/logical-partitions/([^/]+)/operations/open-os-message-channel',
              MessagesChannelHandler),
            ]
        )
        self._urihandler = zhmc_urihandler.UriHandler(new_uris)
    # __init__()

    @staticmethod
    def logon():
        pass
# MockFakedSession

class MockNotificationSource:
    """
    Mock messages interface
    """
    def __init__(self, channel_topic, hmc_host, user, passwd):
        """
        Create an async reader from notifications channel

        Args:
            notification_receiver (zhmcclient.NotificationReceiver):
                an active NotificationReceiver object
            notification_type (str): type of messages to process
        """
        self.msg_queue = [
            'debirf-rescue login:',
            'Password:',
            hmc.MESSAGES_DEFAULT_PATTERN
        ]
        self._stop = False
    # __init__()

    def close(self):
        """
        Close source
        """
        self._stop = True
    # close()

    def notifications(self):
        """
        Get all messages from notification channel.
        Blocking call up to timeout seconds

        Args:
            timeout (number): max seconds to wait

        Returns:
            List: messages
        """
        while not self._stop:
            yield (
                {'notification-type': 'os-message'},
                {'os-messages': [{'message-text': t} for t in self.msg_queue]}
            )
    # notifications()

# MockMessages

class TestHypervisorHmc(TestCase):
    """
    Unit test for the HypervisorHmc class
    """
    def setUp(self):
        """
        Setup a HypervisorHmc object and related mocks.
        """
        self.system_name = 'dummy_cpc'
        self.host_name = 'dummy_hmc.domain.com'
        self.user = 'HMCUSER'
        self.passwd = 'somepwd'
        self.parameters = {}
        self.lpar_name = 'dummy_lpar'

        # replace method by a mock so that we perform validation later
        patcher_send_os = patch.object(zhmcclient.Lpar, 'send_os_command')
        self._mock_send_os = patcher_send_os.start()
        self.addCleanup(patcher_send_os.stop)
        patcher_send_os_dpm = patch.object(
            zhmcclient.Partition, 'send_os_command', new=self._mock_send_os)
        patcher_send_os_dpm.start()
        self.addCleanup(patcher_send_os_dpm.stop)

        self._mock_zhmc_obj = None
        def session_cls_wrapper(*args, **kwargs):
            """
            Wrapper to keep track of FakedSession instantiation
            """
            self._mock_zhmc_obj = MockFakedSession(*args, **kwargs)
            return self._mock_zhmc_obj
        # session_cls_wrapper()
        # mock the zhmcclient session
        patcher_zhmc = patch.object(
            hmc.zhmcclient, 'Session', new=session_cls_wrapper)
        self._mock_zhmc_cls = patcher_zhmc.start()
        self.addCleanup(patcher_zhmc.stop)

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

        def messages_connect(*args, **kwargs):
            """Provide mock notification source to Messages"""
            return hmc.Messages(MockNotificationSource(*args, **kwargs))
        # messages_connect()
        patcher_messages = patch.object(
            hmc.Messages, 'connect', new=messages_connect)
        self._mock_messages_cls = patcher_messages.start()
        self.addCleanup(patcher_messages.stop)

        # instantiate the object to be used in the testcases
        self.hmc_object = hmc.HypervisorHmc(
            self.system_name,
            self.host_name,
            self.user,
            self.passwd,
            self.parameters
        )
        self._set_fakes()
    # setUp()

    def _assert_all_classic(self, fake_lpar, fake_profile, ipl_address,
                            memory, cpu_ifl, cpu_cp, cpu_mode='shared',
                            net_setup=None, net_boot=None):
        """
        Helper to validate results in classic mode
        """
        # validate
        self.assertEqual(fake_lpar.properties['status'], 'operating')
        self.assertEqual(
            fake_lpar.properties['last-used-load-address'], ipl_address)
        img_props = fake_profile.properties
        self.assertEqual(img_props['central-storage'], memory)
        self.assertEqual(img_props['processor-usage'], cpu_mode)
        self.assertEqual(
            img_props['number-shared-general-purpose-processors'], cpu_cp)
        self.assertEqual(
            img_props['number-shared-ifl-processors'], cpu_ifl)

        # validate network setup was executed
        if net_setup:
            self._assert_net_setup(net_setup)
        else:
            self._mock_send_os.assert_not_called()

        # validate netboot occurred
        if net_boot:
            self._assert_net_boot(net_boot)
        # validate netboot was not performed
        else:
            (self._mock_guest_linux.return_value.open_session.
             assert_not_called())
    # _assert_all_classic()

    def _assert_all_dpm(self, fake_part, boot_dev, memory, cpu_ifl, cpu_cp,
                        cpu_mode='shared', net_setup=None, net_boot=None):
        """
        Helper to validate results in DPM mode
        """
        # validate
        self.assertEqual(fake_part.properties['status'], 'active')
        # network boot: verify different properties
        if '://' in boot_dev:
            parsed_url = urlsplit(boot_dev)
            self.assertEqual(
                fake_part.properties['boot-device'], parsed_url.scheme)
            self.assertEqual(
                fake_part.properties['boot-ftp-host'], parsed_url.hostname)
            self.assertEqual(
                fake_part.properties['boot-ftp-username'], parsed_url.username)
            self.assertEqual(
                fake_part.properties['boot-ftp-password'], parsed_url.password)
            self.assertEqual(
                fake_part.properties['boot-ftp-insfile'], parsed_url.path)
        else:
            self.assertEqual(
                fake_part.properties['boot-device'], 'storage-volume')
            self.assertEqual(
                fake_part.properties['boot-storage-volume'], boot_dev)
        self.assertEqual(fake_part.properties['initial-memory'], memory)
        self.assertEqual(fake_part.properties['maximum-memory'], memory)
        self.assertEqual(fake_part.properties['cp-processors'], cpu_cp)
        self.assertEqual(fake_part.properties['ifl-processors'], cpu_ifl)
        self.assertEqual(fake_part.properties['processor-mode'], cpu_mode)

        # validate network setup was executed
        if net_setup:
            self._assert_net_setup(net_setup)
        else:
            self._mock_send_os.assert_not_called()

        # validate netboot occurred
        if net_boot:
            self._assert_net_boot(net_boot)
        # validate netboot was not performed
        else:
            (self._mock_guest_linux.return_value.open_session.
             assert_not_called())
    # _assert_all_dpm()

    def _assert_net_boot(self, net_boot):
        """
        Assert that the netboot occurred as expected.

        Args:
            net_boot (dict): boot parameters used containing kernel info
        """
        # session = self._mock_guest_linux.return_value.open_session.return_value
        session = self._mock_send_os
        kexec_call = mock.call(
            "kexec /tmp/kernel --initrd=/tmp/initrd "
            "--command-line='{}'".format(net_boot["cmdline"])
        )

        # this verification assumes that kernel and initrd will always have
        # same scheme
        parsed_url = urlsplit(net_boot['kernel_url'])
        if parsed_url.scheme in ('http', 'https', 'ftp'):
            calls = [
                mock.call("wget --no-check-certificate -nv -O '/tmp/kernel' "
                          "'{}'".format(net_boot['kernel_url'])),
                mock.call("wget --no-check-certificate -nv -O '/tmp/initrd' "
                          "'{}'".format(net_boot['initrd_url'])),
                kexec_call,
            ]
            session.assert_has_calls(calls)
        else:
            calls = [
                mock.call(net_boot.get("kernel_url"), "/tmp/kernel"),
                mock.call(net_boot.get("initrd_url"), "/tmp/initrd")
            ]
            self._mock_guest_linux.return_value.push_file.assert_has_calls(
                calls)
            session.assert_has_calls([kexec_call])
    # _assert_net_boot()

    def _assert_net_setup(self, net_setup):
        """
        Assert that network setup was properly done.

        Args:
            net_setup (dict): network parameters used
        """
        if net_setup.get('type') == 'pci':
            net_cmd_calls = [
                mock.call("root"),
                mock.call(net_setup['password']),
                mock.call(
                    "DEV_PATH=$(dirname $(grep -m1 -r '0x0*{}' --include "
                    "function_id /sys/bus/pci/devices/*))".format(
                        net_setup['device'])),
                mock.call(
                    "export IFACE_NAME=$(ls -1 ${DEV_PATH}/net | head -1)"
                ),
            ]
        else:
            ch_list = net_setup.get("device").split(",")
            if len(ch_list) > 1:
                cio_expected = net_setup.get("device")
            else:
                chan_2 = hex(int(net_setup.get("device"), 16)+1).strip("0x")
                chan_3 = hex(int(net_setup.get("device"), 16)+2).strip("0x")
                cio_expected = '{},{},{}'.format(
                    net_setup.get("device"), chan_2, chan_3)

            znet_expected = 'znetconf -a {}'.format(
                ch_list[0].replace('0.0', ''))
            options = net_setup.get('options')
            if not options or not options.get('layer2'):
                znet_expected += ' -o layer2=0'
            else:
                for option, value in options.items():
                    znet_expected += ' -o {}={}'.format(option, value)

            # build the list of expected calls
            full_ccw = ch_list[0]
            if '.' not in full_ccw:
                full_ccw = '0.0.{}'.format(full_ccw)
            net_cmd_calls = [
                mock.call("root"),
                mock.call(net_setup['password']),
                mock.call("cio_ignore -r {}".format(cio_expected)),
                mock.call(znet_expected),
                mock.call("export IFACE_NAME=$(ls -1 /sys/devices/qeth/{}/net "
                          "| head -1)".format(full_ccw)),
            ]
            if ' layer2=1 ' in znet_expected and net_setup["mac"]:
                net_cmd_calls.append(
                    mock.call("ip link set $IFACE_NAME address {}".format(
                        net_setup["mac"]))
                )

        if net_setup.get('vlan'):
            net_cmd_calls.extend([
                mock.call('ip link add link ${{IFACE_NAME}} name '
                          '${{IFACE_NAME}}.{vlan} type vlan id {vlan}'
                          .format(**net_setup)),
                mock.call('ip link set $IFACE_NAME up'),
                mock.call('export IFACE_NAME=${{IFACE_NAME}}.{}'.format(
                    net_setup['vlan']))
            ])
        net_cmd_calls.extend([
            mock.call("ip addr add {}/{} dev $IFACE_NAME".format(
                net_setup.get("ip"), net_setup.get("mask"))),
            mock.call("ip link set $IFACE_NAME up"),
            mock.call("ip route add default via {}".format(
                net_setup.get("gateway"))),
        ])
        dns_servers = net_setup.get('dns')
        if dns_servers:
            net_cmd_calls.append(mock.call("echo > /etc/resolv.conf"))
            for dns_entry in dns_servers:
                net_cmd_calls.append(
                    mock.call("echo 'nameserver {}' >> /etc/resolv.conf"
                              .format(dns_entry)))

        net_cmd_calls.append(
            mock.call("ping -c 1 {}".format(net_setup.get('gateway'))))
        self._mock_send_os.assert_has_calls(net_cmd_calls)

    # _assert_net_setup()

    def _set_fakes(self):
        """
        Prepare all zhmmcclient fake resources necessary for testing
        """
        self.hmc_object.login()
        self._fake_cpc = self._mock_zhmc_obj.hmc.cpcs.add({
            'name': self.system_name.upper(),
            'description': 'some_description',
            'processor-count-ifl': 10,
            'processor-count-general-purpose': 10
        })
        # lpar
        self._fake_lpar = self._fake_cpc.lpars.add({
            'name': self.lpar_name.upper(),
            'status': 'not-activated',
            'last-used-load-address': '9999',
            'last-used-logical-unit-number': '0',
            'last-used-world-wide-port-name': '0',
            'next-activation-profile-name': self.lpar_name.upper(),
        })
        # activation profile
        self._fake_img_profile = self._fake_cpc.image_activation_profiles.add({
            'name': self.lpar_name.upper(),
            'central-storage': 4096,
            'number-shared-general-purpose-processors': 1,
            'number-shared-ifl-processors': 1,
            # set as dedicated to test whether it changes to shared
            'processor-usage': 'dedicated',
        })

        # DPM related resources
        fake_console = self._mock_zhmc_obj.hmc.consoles.add({})
        fake_sg_fcp = fake_console.storage_groups.add({
            'name': 'storage group fcp type',
            'type': 'fcp',
        })
        # fcp volume
        self._fake_sv_scsi = fake_sg_fcp.storage_volumes.add({
            'name': 'dummy_volume_scsi',
            'uuid': '987654321',
            'size': '21248',
            # due to a bug in zhmcclient_mock we can't test changing the
            # storage volume usage so we set directly as boot here
            'usage': 'boot',
        })
        fake_sg_dasd = fake_console.storage_groups.add({
            'name': 'storage group fc type',
            'type': 'fc',
        })
        # dasd volume
        self._fake_sv_dasd = fake_sg_dasd.storage_volumes.add({
            'name': 'dummy_volume_dasd',
            'device-number': '0101',
            'size': '10000',
            # due to a bug in zhmcclient_mock we can't test changing the
            # storage volume usage so we set directly as boot here
            'usage': 'boot',
        })
        self._fake_cpc_dpm = self._mock_zhmc_obj.hmc.cpcs.add({
            'dpm-enabled': True,
            'available-features-list': [OrderedDict([
                ('name', 'dpm-storage-management'),
                ('description', 'DPM storage management feature'),
                ('state', True)
            ])],
            'name': '{}_dpm'.format(self.system_name).upper(),
            'description': 'some_description_dpm',
            'processor-count-ifl': 11,
            'processor-count-general-purpose': 13,
        })
        self._fake_part = self._fake_cpc_dpm.partitions.add({
            'initial-memory': 2048,
            'maximum-memory': 2048,
            # set as dedicated to test whether it changes to shared
            'processor-mode': 'dedicated',
            'ifl-processors': 1,
            'cp-processors': 1,
            'name': '{}_dpm'.format(self.lpar_name).lower(),
            'status': 'stopped',
            'storage-group-uris': [
                fake_sg_fcp.properties['object-uri'],
                fake_sg_dasd.properties['object-uri']],
            'available-features-list': [OrderedDict([
                ('name', 'dpm-storage-management'),
                ('description', 'DPM storage management feature'),
                ('state', True)
            ])],
        })
    # _set_fakes()

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

    def test_cpu_dynamic_not_enough(self):
        """
        Check if the dynamic strategy correctly reports error when the
        requested number of generic CPUs exceed the quantity available in the
        CPC.
        """
        # setting up the mock objects
        cpus_cp, cpus_ifl = 2, 2
        self._fake_cpc.update({
            'processor-count-ifl': cpus_cp,
            'processor-count-general-purpose': cpus_ifl
        })
        cpu = 5
        memory = 1024
        parameters = {
            'boot_params': {
                'boot_method': 'dasd',
                'devicenr': '9999'
            }
        }
        error_msg = (
            'Not enough CPUs available in CPC. Requested: {} CPUs. '
            'Available: {} CPs, {} IFLs.'.format(cpu, cpus_cp, cpus_ifl)
        )
        with self.assertRaisesRegex(RuntimeError, error_msg):
            self.hmc_object.start(self.lpar_name, cpu, memory, parameters)
    # test_cpu_dynamic_not_enough()

    def test_cpu_static_not_enough(self):
        """
        Check if the static strategy correctly reports error when the
        requested number of defined-type CPUs exceed the quantity available in
        the CPC.
        """
        # setting up the mock objects
        cpus_cp, cpus_ifl = 2, 2
        self._fake_cpc.update({
            'processor-count-ifl': cpus_cp,
            'processor-count-general-purpose': cpus_ifl
        })

        cpu = 0
        memory = 1024
        parameters = {
            'boot_params': {
                'boot_method': 'dasd',
                'devicenr': '9999'
            },
            'cpus_cp': 2,
            'cpus_ifl': 10
        }
        error_msg = (
            'Not enough CPUs available in CPC. Requested: {} CPs, {} '
            'IFLs. Available: {} CPs, {} IFLs.'.format(
                parameters['cpus_cp'], parameters['cpus_ifl'],
                cpus_cp, cpus_ifl)
        )

        with self.assertRaisesRegex(RuntimeError, error_msg):
            self.hmc_object.start(self.lpar_name, cpu, memory, parameters)
    # test_cpu_static_not_enough()

    def test_cpu_mem_no_change(self):
        """
        Check the case when user doesn't want to update the parameter.
        """
        parameters = {
            'boot_params': {
                'boot_method': 'dasd',
                'devicenr': '9999'
            },
        }
        cpu = 0
        memory = 0

        self.hmc_object.start(self.lpar_name, cpu, memory, parameters)

        # validate
        self._assert_all_classic(
            self._fake_lpar, self._fake_img_profile, '9999',
            self._fake_img_profile.properties['central-storage'],
            self._fake_img_profile.properties['number-shared-ifl-processors'],
            (self._fake_img_profile.
             properties['number-shared-general-purpose-processors']),
            self._fake_img_profile.properties['processor-usage'],
        )
    # test_cpu_mem_no_change()

    def test_errors(self):
        """
        Exercise different error scenarios
        """
        parameters = {
            'boot_params': {
                'boot_method': 'dasd',
                'devicenr': '9999'
            },
        }

        with self.assertRaisesRegex(ValueError, 'LPAR .* does not exist'):
            self.hmc_object.start('dummy', 0, 0, parameters)

        # wrong cpc name
        hmc_object = hmc.HypervisorHmc(
            'wrong_cpc', self.host_name, self.user, self.passwd, self.parameters)
        hmc_object.login()
        with self.assertRaisesRegex(ValueError, 'CPC .* does not exist'):
            hmc_object.start('dummy', 0, 0, parameters)

        # ftp boot in classic mode
        parameters = {
            'boot_params': {
                'boot_method': 'ftp',
                'insfile': 'dummy'
            },
        }
        with self.assertRaisesRegex(ValueError, 'only available in DPM mode'):
            self.hmc_object.start(self.lpar_name, 0, 0, parameters)

        # specifying dynamic and static cpus simultaneously
        wrong_params = {
            'boot_params': {
                'boot_method': 'dasd',
                'devicenr': '1234',
            },
            'cpus_ifl': 1,
            'cpus_cp': 0,
        }
        with self.assertRaisesRegex(ValueError, 'cpu parameter must be 0 '):
            self.hmc_object.start(self.lpar_name, 1, 0, wrong_params)

        # wrong scsi parameters
        wrong_params = {
            'boot_params': {
                'boot_method': 'scsi',
                'uuid': '1234',
            },
        }
        with self.assertRaisesRegex(
                ValueError, 'the scsi DEVNO, WWPN and LUN must be'):
            self.hmc_object.start(self.lpar_name, 0, 0, wrong_params)

        # exercise DPM mode
        dpm_cpc = '{}_dpm'.format(self.system_name)
        self.hmc_object = hmc.HypervisorHmc(
            dpm_cpc, self.host_name, self.user, self.passwd, self.parameters)
        self._set_fakes()

        # wrong scsi parameters
        wrong_params = {
            'boot_params': {
                'boot_method': 'scsi',
                'devicenr': '1234',
                'wwpn': '1234',
                'lun': '1234',
            },
        }
        with self.assertRaisesRegex(ValueError, 'the scsi volume UUID must be'):
            self.hmc_object.start(
                self._fake_part.properties['name'], 0, 0, wrong_params)

        # wrong partition name
        with self.assertRaisesRegex(ValueError, 'Partition .* does not exist'):
            self.hmc_object.start('dummy', 0, 0, parameters)

        # wrong storage volume id
        parameters['boot_params']['boot_method'] = 'dasd'
        parameters['boot_params']['devicenr'] = '0000'
        with self.assertRaisesRegex(ValueError, 'volume .* not found'):
            self.hmc_object.start(
                self._fake_part.properties['name'], 0, 0, parameters)
        # no storage management available
        parameters['boot_params']['devicenr'] = (
            self._fake_sv_dasd.properties['device-number'])
        self._fake_part.update({'available-features-list': []})
        with self.assertRaisesRegex(NotImplementedError, 'Load operation'):
            self.hmc_object.start(
                self._fake_part.properties['name'], 0, 0, parameters)

        # invalid partition status
        self.hmc_object = hmc.HypervisorHmc(
            dpm_cpc, self.host_name, self.user, self.passwd, self.parameters)
        self._set_fakes()
        self._fake_part.update({'status': 'communications-not-active'})
        msg = 'Partition cannot be managed'
        with self.assertRaisesRegex(RuntimeError, msg):
            self.hmc_object.start(
                self._fake_part.properties['name'], 0, 0, parameters)
    # test_errors()

    def test_login(self):
        """
        Check if the login() method works as expected

        Args:
            None

        Raises:
            AssertionError: if validation fails
        """
        # login() was already executed by setup
        self.assertIsInstance(
            self.hmc_object._conn[0], zhmcclient.Client)
        self.assertIsInstance(self.hmc_object._conn[1], MockFakedSession)

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
        # regular scenario
        self.hmc_object.login()
        self.hmc_object.logoff()
        # check if session was really reset
        self.assertIs(self.hmc_object._conn, None)

        # check if exception is raised on logoff performed without previous
        # login
        with self.assertRaises(ConnectionError):
            self.hmc_object.logoff()
    # test_logoff()

    def test_ops_no_login(self):
        """
        Exercise the scenario where operations are called without a previous
        login.
        """
        self.hmc_object.logoff()

        parameters = {
            'boot_params': {
                "boot_method": "dasd",
                "devicenr": "9999"
            }
        }
        with self.assertRaises(ConnectionError):
            self.hmc_object.start('dummy', 'dummy', 'dummy', parameters)
        with self.assertRaises(ConnectionError):
            self.hmc_object.stop('dummy', {})
        with self.assertRaises(ConnectionError):
            self.hmc_object.reboot('dummy', {})
    # test_ops_no_login()

    def test_param_none(self):
        """
        Confirm that the constructor accepts also None as value for the
        'parameter' attribute and works correctly.
        """
        hmc_object = hmc.HypervisorHmc(
            self.system_name, self.host_name, self.user, self.passwd, None)
        hmc_object.login()
        self.assertIsInstance(self.hmc_object._conn[1], MockFakedSession)
    # test_param_none()

    def test_reboot(self):
        """
        Check if the reboot() method works as expected

        Args:
            None

        Raises:
            AssertionError: if validation fails
        """
        # reboot dasd
        orig_address = self._fake_lpar.properties['last-used-load-address']
        self.hmc_object.reboot(self.lpar_name, {})
        self.assertEqual(self._fake_lpar.properties['status'], 'operating')
        self.assertEqual(
            self._fake_lpar.properties['last-used-load-address'], orig_address)

        # reboot scsi
        orig_address = '1234'
        orig_wwpn = '987654321'
        orig_lun = '123456789'
        self._fake_lpar.properties.update({
            'last-used-load-address': orig_address,
            'last-used-world-wide-port-name': orig_wwpn,
            'last-used-logical-unit-number': orig_lun,
        })
        self.hmc_object.reboot(self.lpar_name, {})
        self.assertEqual(self._fake_lpar.properties['status'], 'operating')
        self.assertEqual(
            self._fake_lpar.properties['last-used-load-address'], orig_address)
        self.assertEqual(
            self._fake_lpar.properties['last-used-world-wide-port-name'],
            orig_wwpn)
        self.assertEqual(
            self._fake_lpar.properties['last-used-logical-unit-number'],
            orig_lun)

        # exercise DPM mode
        dpm_cpc = '{}_dpm'.format(self.system_name)
        self.hmc_object = hmc.HypervisorHmc(
            dpm_cpc, self.host_name, self.user, self.passwd, self.parameters)
        self._set_fakes()

        self.hmc_object.reboot(self._fake_part.properties['name'], {})

        # validate
        self.assertEqual(self._fake_part.properties['status'], 'active')

        # reboot a partition already running
        self.hmc_object.reboot(self._fake_part.properties['name'], {})
        self.assertEqual(self._fake_part.properties['status'], 'active')
    # test_reboot()

    def test_start_dasd_update_dynamic(self):
        """
        Check if the start() method works as expected for a DASD based
        activation and update of the resources. It also validates that the
        dynamic cpu allocation works correctly by assigning all available IFLs
        before assigning CPs.

        Args:
            None

        Raises:
            AssertionError: if validation fails
        """
        # perform the operation when the image profile needs to update cpu
        # and memory using a DASD disk
        cpu = 14
        memory = 1024
        parameters = {
            'boot_params': {
                'boot_method': 'dasd',
                'devicenr': '9999',
            }
        }
        self.hmc_object.start(self.lpar_name, cpu, memory, parameters)

        # validate
        self._assert_all_classic(
            self._fake_lpar, self._fake_img_profile, '9999', memory, 10, 4)

        # exercise DPM mode
        dpm_cpc = '{}_dpm'.format(self.system_name)
        self.hmc_object = hmc.HypervisorHmc(
            dpm_cpc, self.host_name, self.user, self.passwd, self.parameters)
        self._set_fakes()

        parameters['boot_params']['devicenr'] = (
            self._fake_sv_dasd.properties['device-number'])
        self.hmc_object.start(
            self._fake_part.properties['name'], cpu, memory, parameters)

        self._assert_all_dpm(
            self._fake_part, self._fake_sv_dasd.properties['element-uri'],
            memory, 11, 3)

        # try to start an already started partition to make sure stop is used
        # before updating properties
        cpu -= 1
        self.hmc_object.start(
            self._fake_part.properties['name'], cpu, memory, parameters)

        self._assert_all_dpm(
            self._fake_part, self._fake_sv_dasd.properties['element-uri'],
            memory, 11, 2)
    # test_start_dasd_update_dynamic()

    def test_start_already_started(self):
        """
        Exercise the case where the partition is already active
        """
        dpm_cpc = '{}_dpm'.format(self.system_name)
        self.hmc_object = hmc.HypervisorHmc(
            dpm_cpc, self.host_name, self.user, self.passwd, self.parameters)
        self._set_fakes()
        self._fake_part.update({'status': 'active'})

        parameters = {
            'boot_params': {
                'boot_method': 'scsi',
                'uuid': self._fake_sv_scsi.properties['uuid'],
            },
        }
        self.hmc_object.start(
            self._fake_part.properties['name'], 0, 0, parameters)

        self._assert_all_dpm(
            self._fake_part, self._fake_sv_scsi.properties['element-uri'],
            self._fake_part.properties['initial-memory'],
            self._fake_part.properties['ifl-processors'],
            self._fake_part.properties['cp-processors'],
            # dedicated because we don't touch the properties
            'dedicated')

        parameters = {
            'boot_params': {
                'boot_method': 'ftp',
                'insfile': 'user:password@server.example._com/files/image.ins',
            },
        }
        self.hmc_object.start(
            self._fake_part.properties['name'], 0, 0, parameters)

        self._assert_all_dpm(
            self._fake_part, 'ftp://{}'.format(
                parameters['boot_params']['insfile']),
            self._fake_part.properties['initial-memory'],
            self._fake_part.properties['ifl-processors'],
            self._fake_part.properties['cp-processors'],
            # dedicated because we don't touch the properties
            'dedicated')

    # test_start_already_started()

    def test_start_ftp(self):
        """
        Exercise ftp boot in DPM mode.
        """
        parameters = {
            'boot_params': {
                'boot_method': 'ftp',
                'insfile': 'user:password@server.example._com/files/image.ins',
                'netsetup': {
                    "mac": None,
                    "ip": "9.9.9.9",
                    "mask": 24,
                    "gateway": "9.9.9.1",
                    "device": "f500,f501,f502",
                    "password": "super_password",
                    "dns": ['9.9.9.25', '9.9.9.30'],
                    "type": "osa",
                }
            }
        }
        cpu = 3
        memory = 2048

        dpm_cpc = '{}_dpm'.format(self.system_name)
        self.hmc_object = hmc.HypervisorHmc(
            dpm_cpc, self.host_name, self.user, self.passwd, self.parameters)
        self._set_fakes()

        self.hmc_object.start(
            self._fake_part.properties['name'], cpu, memory, parameters)

        self._assert_all_dpm(
            self._fake_part,
            '{boot_method}://{insfile}'.format(**parameters['boot_params']),
            memory, 3, 0, net_setup=parameters['boot_params']['netsetup'])
    # test_start_ftp()

    def test_start_scsi_update_static(self):
        """
        Check if the start() method works as expected for a SCSI based
        activation and static cpu allocation.
        """
        parameters = {
            'boot_params': {
                'boot_method': 'scsi',
                'devicenr':'0.2.1234',
                'wwpn': '4321',
                'lun': '1324'
            },
            'cpus_ifl': 7,
            'cpus_cp': 2,
        }
        cpu = 0
        memory = 4096
        self.hmc_object.start(self.lpar_name, cpu, memory, parameters)

        # validate (zhmmclient_mock._session.LparLoadHandler.post does not
        # store wwpn/lun so we can't check it
        normalized_devicenr = parameters['boot_params']['devicenr'].replace(
            '.', '')[-5:]
        self._assert_all_classic(
            self._fake_lpar, self._fake_img_profile,
            normalized_devicenr, memory,
            parameters['cpus_ifl'], parameters['cpus_cp'])

        # exercise DPM mode
        dpm_cpc = '{}_dpm'.format(self.system_name)
        self.hmc_object = hmc.HypervisorHmc(
            dpm_cpc, self.host_name, self.user, self.passwd, self.parameters)
        self._set_fakes()

        parameters = {
            'boot_params': {
                'boot_method': 'scsi',
                'uuid': self._fake_sv_scsi.properties['uuid'],
            },
            'cpus_ifl': 7,
            'cpus_cp': 2,
        }
        self.hmc_object.start(
            self._fake_part.properties['name'], cpu, memory, parameters)

        self._assert_all_dpm(
            self._fake_part, self._fake_sv_scsi.properties['element-uri'],
            memory, parameters['cpus_ifl'], parameters['cpus_cp'])
    # test_start_scsi_update_static()

    def test_start_netsetup(self):
        """
        Test start operation with auto network setup using VLAN
        """
        lpar_name = 'dummy_lpar'
        parameters = {
            'boot_params': {
                'boot_method': 'scsi',
                'devicenr':'1234',
                'wwpn': '4321',
                'lun': '1324',
                # test passing uuid as well
                'uuid':'123456789',
                'netsetup': {
                    "mac": None,
                    "ip": "9.9.9.9",
                    "mask": 24,
                    "gateway": "9.9.9.1",
                    "device": "f500,f501,f502",
                    "password": "super_password",
                    "dns": ['9.9.9.25', '9.9.9.30'],
                    "type": "osa",
                    "vlan": 55,
                }
            },
            'cpus_ifl': 1
        }
        cpu = 0
        memory = 4096

        self.hmc_object.start(lpar_name, cpu, memory, parameters)

        # validate
        self._assert_all_classic(
            self._fake_lpar, self._fake_img_profile,
            parameters['boot_params']['devicenr'], memory,
            parameters['cpus_ifl'], 0,
            net_setup=parameters['boot_params']['netsetup'])
    # test_start_netsetup()

    def test_start_netsetup_pci_no_update(self):
        """
        Test start operation with auto network setup using a pci card.
        Also test the case when the resoures requested match the current
        configuration.
        """
        parameters = {
            'boot_params': {
                'boot_method': 'scsi',
                'devicenr':'1234',
                'wwpn': '4321',
                'lun': '1324',
                'netsetup': {
                    "mac": None,
                    "ip": "9.9.9.9",
                    "mask": 24,
                    "gateway": "9.9.9.1",
                    "device": "500",
                    "password": "super_password",
                    "dns": ['9.9.9.25', '9.9.9.30'],
                    "type": "pci",
                }
            },
            'cpus_ifl': (
                self._fake_img_profile.
                properties['number-shared-ifl-processors']),
            'cpus_cp': (
                self._fake_img_profile.
                properties['number-shared-general-purpose-processors']),
        }
        cpu = 0
        memory = self._fake_img_profile.properties['central-storage']
        self._fake_img_profile.update({'processor-usage': 'shared'})

        self.hmc_object.start(self.lpar_name, cpu, memory, parameters)

        # validate
        self._assert_all_classic(
            self._fake_lpar, self._fake_img_profile,
            parameters['boot_params']['devicenr'], memory,
            parameters['cpus_ifl'], parameters['cpus_cp'],
            net_setup=parameters['boot_params']['netsetup'])

        # exercise DPM mode
        dpm_cpc = '{}_dpm'.format(self.system_name)
        self.hmc_object = hmc.HypervisorHmc(
            dpm_cpc, self.host_name, self.user, self.passwd, self.parameters)
        self._set_fakes()
        self._fake_part.update({'processor-mode': 'shared'})

        memory = self._fake_part.properties['initial-memory']
        parameters['cpus_ifl'] = (
            self._fake_part.properties['ifl-processors'])
        parameters['cpus_cp'] = (
            self._fake_part.properties['cp-processors'])
        parameters['boot_params']['uuid'] = (
            self._fake_sv_scsi.properties['uuid'])
        parameters['boot_params'].pop('lun')
        parameters['boot_params'].pop('wwpn')
        parameters['boot_params'].pop('devicenr')

        self.hmc_object.start(
            self._fake_part.properties['name'], cpu, memory, parameters)

        self._assert_all_dpm(
            self._fake_part, self._fake_sv_scsi.properties['element-uri'],
            memory, parameters['cpus_ifl'], parameters['cpus_cp'],
            net_setup=parameters['boot_params']['netsetup'])
    # test_start_netsetup_pci()

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
                    "mask": 24,
                    "gateway": "9.9.9.1",
                    "device": "f500,f501,f502",
                    "password": "super_password",
                },
                'netboot': {
                    "cmdline": "some_cmdline",
                    # exercise http URLs
                    "kernel_url": "http://some_url",
                    "initrd_url": "http://some_url",
                }
            },
        }
        cpu = 6
        memory = 4096

        self.hmc_object.start(lpar_name, cpu, memory, parameters)

        # validate
        self._assert_all_classic(
            self._fake_lpar, self._fake_img_profile,
            parameters['boot_params']['devicenr'], memory, cpu, 0,
            net_setup=parameters['boot_params']['netsetup'],
            net_boot=parameters['boot_params']['netboot'])
    # test_start_netsetup_netboot()

    def test_stop(self):
        """
        Check if the stop() method works as expected

        Args:
            None

        Raises:
            AssertionError: if validation fails
        """
        self.hmc_object.stop(self.lpar_name, {})

        # validate
        self.assertEqual(self._fake_lpar.properties['status'], 'not-activated')

        # exercise DPM mode
        dpm_cpc = '{}_dpm'.format(self.system_name)
        self.hmc_object = hmc.HypervisorHmc(
            dpm_cpc, self.host_name, self.user, self.passwd, self.parameters)
        self._set_fakes()
        self._fake_part.update({'status': 'active'})

        self.hmc_object.stop(self._fake_part.properties['name'], {})

        # validate
        self.assertEqual(self._fake_part.properties['status'], 'stopped')

        # test stop on stopped partition (operation is skipped)
        self.hmc_object.stop(self._fake_part.properties['name'], {})
    # test_stop()

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
                    "mask": 24,
                    "gateway": "9.9.9.1",
                    # test with a different channel format
                    "device": "f500",
                    "password": "somepwd",
                },
                'netboot': {
                    "cmdline": "some_cmdline",
                    # exercise ftp URLs
                    "kernel_url": "ftp://some_url",
                    "initrd_url": "ftp://some_url",
                }
            }
        }

        self.hmc_object.start(lpar_name, cpu, memory, parameters)
        net_setup = parameters['boot_params']['netsetup']
        self._assert_all_classic(
            self._fake_lpar, self._fake_img_profile,
            parameters['boot_params']['devicenr'], memory, cpu, 0,
            net_setup=net_setup, net_boot=parameters['boot_params']['netboot'])

        # test with layer2 on and additional options
        # by using an ordered dict and placing layer2 on second position we
        # validate that layer2 always comes first
        net_setup['options'] = OrderedDict()
        net_setup['options']['layer2'] = '1'
        net_setup['options']['portname'] = 'osaport'
        net_setup['options']['portno'] = '0'
        net_setup['options']['buffer_count'] = '128'
        self._mock_send_os.reset_mock()
        self.hmc_object.start(lpar_name, cpu, memory, parameters)
        self._assert_all_classic(
            self._fake_lpar, self._fake_img_profile,
            parameters['boot_params']['devicenr'], memory, cpu, 0,
            net_setup=net_setup, net_boot=parameters['boot_params']['netboot'])

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
                    "mask": 24,
                    "gateway": "9.9.9.1",
                    # test with a different channel format
                    "device": "f500",
                    "password": "somepwd",
                },
                # exercise ssh URLs
                'netboot': {
                    "cmdline": "some_cmdline",
                    "kernel_url": "ssh://some_url",
                    "initrd_url": "ssh://some_url",
                }
            }
        }

        # by using an ordered dict and placing layer2 on second position we
        # validate that layer2 always comes first
        net_setup = parameters['boot_params']['netsetup']
        net_setup['options'] = OrderedDict()
        net_setup['options']['layer2'] = '1'
        net_setup['options']['portname'] = 'osaport'
        net_setup['options']['portno'] = '0'
        net_setup['options']['buffer_count'] = '128'
        self.hmc_object.start(lpar_name, cpu, memory, parameters)
        self._assert_all_classic(
            self._fake_lpar, self._fake_img_profile,
            parameters['boot_params']['devicenr'], memory, cpu, 0,
            net_setup=net_setup, net_boot=parameters['boot_params']['netboot'])

    # test_start_netboot_layer2_no_mac()

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
        cpu = 6
        memory = 4096

        parameters = {
            "boot_params": {
                'boot_method': 'scsi',
                'devicenr':'1234',
                'wwpn': '4321',
                'lun': '1324',
                'netsetup': {
                    "mac": "ff:ff:ff:ff:ff:ff",
                    "ip": "9.9.9.9",
                    "mask": 24,
                    "gateway": "9.9.9.1",
                    "device": "f500,f501,f502",
                    "password": "super_password",
                    "dns": ['9.9.9.25', '9.9.9.30']
                },
                'netboot': {
                    "cmdline": "some_cmdline",
                    "kernel_url": "ssh://some_url/kernel",
                    "initrd_url": "ssh://some_url/initrd",
                }
            }
        }

        # set the subprocess mock so that the network configuration fails
        self._mock_guest_linux.return_value.push_file.side_effect = Exception()

        error_msg = 'Failed to upload ssh://some_url/kernel'
        with self.assertRaisesRegex(RuntimeError, error_msg):
            self.hmc_object.start(self.lpar_name, cpu, memory, parameters)
    # test_start_netboot_network_timeout()
# TestHypervisorHmc
