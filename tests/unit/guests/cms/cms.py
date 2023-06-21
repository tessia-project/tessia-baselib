# Copyright 2018 IBM Corp.
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
Test module for cms guest
"""

#
# IMPORTS
#
from tessia.baselib.common.s3270 import terminal
from tessia.baselib.guests.cms import cms
from unittest import mock
from unittest import TestCase
from unittest.mock import patch

import os
import re
import yaml

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#
def patch_s3270(test_obj, mock_outputs):
    """
    Mock the s3270 object of the passed GuestCms object. This function is
    defined outside the testcase class because it is also consumed by the zvm
    hypervisor testcase.
    Here we patch one level below - the S3270 class - so that we can mock
    actual console outputs. This is a more meaningful test as we can validate
    the correctness of the regexes. In addition, it would be difficult to mock
    the returned regex objects if we patched the terminal instead.

    Args:
        test_obj (TestCase): testcase class instance
        mock_outputs (list): list of mocked console outputs to use

    Returns:
        MagicMock: mocked s3270 object
    """
    patcher = patch.object(terminal, 'S3270', autospec=True)
    mock_s3270 = patcher.start().return_value
    test_obj.addCleanup(patcher.stop)
    mock_s3270.host_name = None
    def mock_connect(host_name, *_, **__):
        """
        Set the hostname when called, like the original method.
        """
        mock_s3270.host_name = host_name
    # mock_connect()
    mock_s3270.connect = mock_connect
    mock_s3270.query.return_value = (
        'data: host {0} 23\nU F U C({0}) \nok\n'.format(
            test_obj._hostname)
    )

    # patch the s3280.ascii() function to keep returning the last output when
    # the output list is fully consumed, simulating the real behavior of the
    # console
    def gen_mock_ascii(*_, **__):
        """
        Mock of the ascii method
        """
        index = 0
        while True:
            try:
                ret = mock_outputs[index]
                index += 1
            except IndexError:
                ret = mock_outputs[-1]
            yield ret
    # gen_mock_ascii
    mock_ascii = gen_mock_ascii()
    mock_s3270.ascii.side_effect = lambda *args, **kwargs: next(mock_ascii)

    # patch time.time
    patcher = patch.object(terminal, 'time', autospec=True)
    test_obj._mock_time = patcher.start()
    test_obj.addCleanup(patcher.stop)
    def time_gen():
        """
        Generator to simulate a call to time.time()
        """
        start = 1.0
        yield start
        while True:
            start += 1
            yield start
    # time_gen
    mock_time = time_gen()
    test_obj._mock_time.side_effect = lambda: next(mock_time)

    # patch sleep
    patcher = patch.object(terminal, 'sleep', autospec=True)
    patcher.start()
    test_obj.addCleanup(patcher.stop)

    return mock_s3270
# patch_s3270()

class TestGuestCms(TestCase):
    """
    Unit test for the GuestCms class
    """
    @classmethod
    def setUpClass(cls):
        """
        Store the console output data to be used in the tests.
        """
        data_file = '{}/cms.yaml'.format(
            os.path.dirname(os.path.abspath(__file__)))
        with open(data_file, 'r', encoding='utf-8') as data_fd:
            cls._data = yaml.safe_load(data_fd.read())

        cls._user = 'USER'
        cls._hostname = 'hostname.com'
        cls._passwd = 'password'
    # setUpClass()

    def setUp(self):
        """
        Set up the common mocks for the testcases
        """
        # create guest object
        self._guest = cms.GuestCms(
            self._user, self._hostname, self._user, self._passwd, None)
        # mock guest object's terminal object
        patcher = patch.object(
            self._guest, '_terminal', autospec=True)
        self._mock_terminal = patcher.start()
        # simple mock to have login() to work
        self._mock_terminal.send_cmd.return_value = (
            'Some logon output',
            re.search('Ready;', 'Content\nReady;\n')
        )

        self.addCleanup(patcher.stop)
    # setUp()

    def test_init_error(self):
        """
        Test incorrect initialization of object
        """
        with self.assertRaisesRegex(
                ValueError, 'name must be equal to the username'):
            cms.GuestCms(self._hostname, self._hostname, self._user,
                         self._passwd, None)
    # test_init_error()

    def test_hotplug_ok(self):
        """
        Exercise successfully hotplugging cpu, disks and network interfaces.
        """
        # create guest object
        guest_obj = cms.GuestCms(
            self._user, self._hostname, self._user, self._passwd, None)
        # mock the expected console output
        mock_s3270 = patch_s3270(
            self, self._data['hotplug_ok'])

        # create new instance of terminal
        guest_cpu = 3
        disks = [
            # dasd
            {"type": "dasd", "devno": "1c5d"},
            # scsi
            {
                "type": "fcp",
                "adapters": [
                    {"devno": "1740", "wwpns": ["100507630503c5ae"]},
                    {"devno": "0.0.1780", "wwpns": ["100507630503c7ae"]},
                ],
                "lun": "1022400d00000000",
            }
        ]
        ifaces = [
            # osa
            {"type": "osa", "id": "f5f0,f5f1,f5f2"},
            # pci
            {"type": "pci", "id": "240"},
            {"type": "pci", "id": "250"},
        ]
        guest_ext = {'ifaces': ifaces}
        guest_obj.login()
        guest_obj.hotplug(cpu=guest_cpu, vols=disks, extensions=guest_ext)

        # validate commands executed on console
        call_list = [
            mock.call('l {} noipl'.format(self._user)),
            mock.call(self._passwd, hide=True),
            mock.call('begin'),
            mock.call('#cp term more 50 10'),
            mock.call('#cp i cms'),
            mock.call('access (noprof'),
            mock.call('#cp term more 50 10'),
            mock.call('q v cpus'),
            mock.call('define cpu 2'),
            mock.call('define cpu 3'),
            mock.call('define cpu 4'),
            mock.call('q v  1c5d'),
            mock.call('att  1c5d *'),
            mock.call('q v  1740'),
            mock.call('att  1740 *'),
            mock.call('q v  1780'),
            mock.call('att  1780 *'),
            mock.call('q v  f5f0'),
            mock.call('q v  f5f1'),
            mock.call('q v  f5f2'),
            mock.call('q v pcif 240'),
            mock.call('att pcif 240 *'),
            mock.call('q v pcif 250'),
        ]
        self.assertListEqual(mock_s3270.string.mock_calls, call_list)
    # test_hotplug_ok()

    def test_hotplug_cpu_query_error(self):
        """
        Exercise error in querying cpu during hotplug
        """
        guest_obj = cms.GuestCms(
            self._user, self._hostname, self._user, self._passwd, None)
        # simulate error when querying existing cpus by mocking the expected
        # console output
        mock_output = []
        for output in self._data['hotplug_ok']:
            if output.find('q v cpus') > 0:
                output = re.sub('CPU [0-9A-Fa-f]+',
                                'HCP052E Error in CP directory',
                                output)
                mock_output.append(output)
                break
            mock_output.append(output)
        patch_s3270(self, mock_output)

        # perform action
        guest_cpu = 3
        guest_obj.login()
        with self.assertRaisesRegex(RuntimeError, 'Query CPUs failed with:'):
            guest_obj.hotplug(cpu=guest_cpu)
    # test_hotplug_cpu_query_error()

    def test_hotplug_cpu_define_error(self):
        """
        Exercise error in defining cpu during hotplug
        """
        guest_obj = cms.GuestCms(
            self._user, self._hostname, self._user, self._passwd, None)

        # simulate error when defining new cpus
        mock_outputs = []
        for output in self._data['hotplug_ok']:
            if output.find(' define cpu ') > 0:
                output = re.sub('CPU [0-9A-Fa-f]+ defined',
                                'HCP052E Error in CP directory',
                                output)
                mock_outputs.append(output)
                break
            mock_outputs.append(output)
        patch_s3270(self, mock_outputs)

        guest_cpu = 3
        guest_obj.login()
        with self.assertRaisesRegex(
                RuntimeError, r'Define CPU\(s\) failed with'):
            guest_obj.hotplug(cpu=guest_cpu)
    # test_hotplug_cpu_define_error()

    def test_hotplug_dev_query_error(self):
        """
        Exercise error in querying device during hotplug
        """
        guest_obj = cms.GuestCms(
            self._user, self._hostname, self._user, self._passwd, None)
        # simulate an unexpected output when querying device
        mock_outputs = []
        for output in self._data['hotplug_ok']:
            if output.find('q v  1c5d') > 0:
                output = re.sub('HCPQVD040E Device 1C5D',
                                'DUMMY',
                                output)
                mock_outputs.append(output)
                break
            mock_outputs.append(output)
        patch_s3270(self, mock_outputs)

        # perform action
        guest_cpu = 3
        disk_dasd = {"type": "dasd", "devno": "1c5d"}
        guest_obj.login()
        exp_re = 'Query device 1c5d returned unexpected output'
        with self.assertRaisesRegex(RuntimeError, exp_re):
            guest_obj.hotplug(cpu=guest_cpu, vols=[disk_dasd])
    # test_hotplug_dev_query_error()

    def test_hotplug_dev_att_error(self):
        """
        Exercise error in attaching device during hotplug
        """
        guest_obj = cms.GuestCms(
            self._user, self._hostname, self._user, self._passwd, None)
        # inject an unexpected output after attaching device
        mock_outputs = []
        for output in self._data['hotplug_ok']:
            if output.find('att  1c5d *') > 0:
                output = re.sub('1C5D ATTACHED',
                                'DUMMY',
                                output)
                mock_outputs.append(output)
                break
            mock_outputs.append(output)
        patch_s3270(self, mock_outputs)

        # perform action
        guest_cpu = 3
        disk_dasd = {"type": "dasd", "devno": "1c5d"}
        guest_obj.login()
        exp_re = 'Attach device 1c5d returned unexpected output'
        with self.assertRaisesRegex(RuntimeError, exp_re):
            guest_obj.hotplug(cpu=guest_cpu, vols=[disk_dasd])
    # test_hotplug_dev_att_error()

    def test_install_packages(self):
        """
        Verify that the install_packages method is unsupported
        """
        self.assertRaises(
            NotImplementedError, self._guest.install_packages, [])
    # test_open_session()

    def test_login_ok(self):
        """
        Exercise a normal login command
        """
        self._mock_terminal.send_cmd.return_value = (
            'Some logon output',
            re.search('Ready;', 'Content\nReady;\n')
        )

        self._guest.login()
        self._mock_terminal.login.assert_called_once_with(
            self._hostname, self._user.upper(), self._passwd,
            {'noipl': True}, 60
        )
    # test_login_ok()

    def test_logoff(self):
        """
        Exercise a normal logoff command
        """
        self._mock_terminal.send_cmd.return_value = (
            'Some logon output',
            re.search('Ready;', 'Content\nReady;\n')
        )

        self._guest.login()
        self._guest.logoff()
        self._mock_terminal.disconnect.assert_called_once_with()
    # test_logoff()

    def test_open_session(self):
        """
        Verify that the open_session method is unsupported
        """
        self.assertRaises(OSError, self._guest.open_session)
    # test_open_session()

    def test_pull_file(self):
        """
        Verify that pull_file is unsupported.
        """
        self.assertRaises(NotImplementedError, self._guest.pull_file)
    # test_pull_file()

    def test_push_error(self):
        """
        Exercise various scenarios where an error occurs when trying to push a
        file.
        """
        src_file = '/source/file'
        target_file = 'TARGET FILE A'

        # invalid url scheme
        self._guest.login()
        with self.assertRaisesRegex(ValueError, 'Invalid url scheme'):
            self._guest.push_file('wrong://{}'.format(src_file), target_file)

        # local file does not exist
        patcher = patch.object(cms.os.path, 'exists', autospec=True)
        mock_exists = patcher.start()
        self.addCleanup(patcher.stop)
        mock_exists.return_value = False
        with self.assertRaisesRegex(ValueError, 'does not exist'):
            self._guest.push_file('file://{}'.format(src_file), target_file)

        # url not accessible
        patcher = patch.object(cms.requests, 'get', autospec=True)
        mock_get = patcher.start()
        self.addCleanup(patcher.stop)
        mock_resp = mock_get.return_value
        mock_exc = cms.requests.exceptions.RequestException()
        mock_exc.response = mock.Mock()
        mock_exc.response.status_code = 404
        mock_exc.response.reason = 'Not found'
        mock_resp.raise_for_status.side_effect = mock_exc
        with self.assertRaisesRegex(
                ValueError, 'Source url is not accessible: 404 Not found'):
            self._guest.push_file('http://{}'.format(src_file), target_file)

    # test_push_error()

    def test_push_local_file(self):
        """
        Exercise uploading a local file to the guest.
        """
        patcher = patch.object(cms.os.path, 'exists', autospec=True)
        mock_exists = patcher.start()
        self.addCleanup(patcher.stop)
        mock_exists.return_value = True

        self._mock_terminal.transfer.return_value = (
            'Transfer complete, 28337936 bytes transferred\n'
            '4.48 Mbytes/sec in DFT mode'
        )
        self._guest.login()
        src_file = '/source/file'
        target_file = 'TARGET FILE A'
        self._guest.push_file('file://{}'.format(src_file), target_file)

        # validate behavior
        mock_exists.assert_called_once_with(src_file)
        self._mock_terminal.transfer.assert_called_once_with(
            src_file, target_file, direction='send',
            timeout=cms.TRANSFER_TIMEOUT, mode='binary')
    # test_push_local_file()

    def test_push_http_file(self):
        """
        Exercise uploading a file from a http url to the guest.
        """
        # mock requests.get
        patcher = patch.object(cms.requests, 'get', autospec=True)
        mock_get = patcher.start()
        self.addCleanup(patcher.stop)
        mock_resp = mock_get.return_value
        mock_resp.raise_for_status.return_value = None
        mock_resp.iter_content.return_value = ['1', '2', '3']

        # mock temp file creation
        patcher = patch.object(cms, 'NamedTemporaryFile', autospec=True)
        mock_temp_cls = patcher.start()
        self.addCleanup(patcher.stop)
        mock_file = mock_temp_cls.return_value.__enter__.return_value
        mock_file.name = 'local_temp_file'

        self._mock_terminal.transfer.return_value = (
            'Transfer complete, 28337936 bytes transferred\n'
            '4.48 Mbytes/sec in DFT mode'
        )
        self._guest.login()
        src_file = 'http://host.com/file'
        target_file = 'TARGET FILE A'
        self._guest.push_file(src_file, target_file)

        # validate behavior
        mock_resp.iter_content.assert_called_once_with(chunk_size=mock.ANY)
        template_for_checking = [
            mock.call('1'),
            mock.call('2'),
            mock.call('3'),
        ]

        self.assertIn(template_for_checking, mock_file.write.mock_calls)
        self._mock_terminal.transfer.assert_called_once_with(
            mock_file.name, target_file, direction='send',
            timeout=cms.TRANSFER_TIMEOUT, mode='binary')
    # test_push_http_file()

    def test_run(self):
        """
        Exercise the run method.
        """
        ret_cmd = ('Some output', re.search('output', 'output'))
        # mock return of login and then return of command
        self._mock_terminal.send_cmd.side_effect = [
            ('z/VM 6.4', re.search('z/VM', 'Content\nz/VM 6.4\n')),
            ('Some logon output', re.search('Ready;', 'Content\nReady;\n')),
            ('TERM MORE OUTPUT', None),
            ret_cmd,
        ]

        self._guest.login()
        output, re_match = self._guest.run('some_cmd')
        self.assertMultiLineEqual(output, ret_cmd[0])
        self.assertIs(re_match, ret_cmd[1])
    # test_run()

    def test_stop(self):
        """
        Exercise a normal stop command
        """
        self._guest.login()
        self._guest.stop()
        self._mock_terminal.send_cmd.assert_called_with(
            'system clear', True)
        self._mock_terminal.logoff.assert_called_once_with()
    # test_stop()

    # TODO: test attach of pci device
    # TODO: test definition of virtual interfaces
# TestGuestCms
