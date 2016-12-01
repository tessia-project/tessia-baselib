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
Module for HypervisorKvm class
"""

#
# IMPORTS
#
from tessia_baselib.common.logger import get_logger
from tessia_baselib.common.params_validators.utils import validate_params
from tessia_baselib.guests.linux.linux import GuestLinux
from tessia_baselib.hypervisors.base import HypervisorBase
from tessia_baselib.hypervisors.kvm.guest import GuestKvm
from tessia_baselib.hypervisors.kvm.virsh import Virsh

#
# CONSTANTS AND DEFINITIONS
#

#
# CODE
#

class HypervisorKvm(HypervisorBase):
    """
    This class implements the driver to support the KVM hypervisor type
    """

    # the identifier for this hypervisor class
    HYP_ID = 'kvm'

    @validate_params
    def __init__(self, system_name, host_name, user,
                 passwd, parameters):
        """
        Constructor

        Args:
            system_name (string): string containing the hypervisor name
            host_name (string): hostname or ip address of system
            user (string): user to login to system
            passwd (string): password to login to system
            parameters (dict): a dictionary containing values specific to each
                        hypervisor type

        Returns:
            None

        Raises:
            None
        """
        super().__init__(system_name, host_name, user,
                         passwd, parameters)

        self._logger = get_logger(__name__)

        self._logger.debug(
            "create HypervisorKvm: name='%s' host_name='%s' user='%s' "
            "parameters='%s'",
            self.name,
            self.host_name,
            self.user,
            str(self.parameters)
        )

        # a KVM hypervisor is also a linux guest, so we establish connection
        # with it using the GuestLinux class.
        self._host_cnn = GuestLinux(system_name, host_name, user,
                                    passwd, parameters)
        self._host_session = None
    # __init__()

    def _test_logged_in(self):
        """
        Auxiliary Method. Test if we are logged in the system
        before performing any operation.

        Args:
            None

        Returns:
            None

        Raises:
            RuntimeError: if it is not logged in the system.
        """
        if self._host_session is None:
            raise RuntimeError("You must login first")
    # _test_logged_in()

    def login(self, timeout=60):
        """
        Execute the login to the hypervisor system using the credentials
        provided.

        Args:
            timeout (int): how many seconds to wait for connection

        Returns:
            None

        Raises:
            None
        """
        self._logger.debug(
            "performing LOGIN HypervisorKvm: name='%s' host_name='%s' "
            "user='%s' parameters='%s'",
            self.name,
            self.host_name,
            self.user,
            str(self.parameters)
        )

        if self._host_session is not None:
            self._logger.warning(
                "Login called with connection already active:"
                " dropping previous connection object"
            )

        self._host_cnn.login(timeout)
        self._host_session = self._host_cnn.open_session()
    # login()

    def logoff(self):
        """
        Close an active connection to the hypervisor system

        Args:
            None

        Returns:
            None

        Raises:
            RuntimeError: It is not logged in the guest
        """
        self._test_logged_in()

        self._logger.debug("performing LOGOFF HypervisorKVM")

        self._host_session.close()
        self._host_cnn.logoff()
        self._host_session = None
    # logoff()

    @validate_params
    def start(self, guest_name, cpu, memory, parameters):
        """
        Attach the given resources and start the guest using the method
        and devices specified.

        Args:
            guest_name (string):  Name of the guest as known by hypervisor
            cpu (int):            Number of CPU's to assign.
            memory (int):         Amount of memory to assin in megabytes.
            parameters (dict):    A dictionary containing values specific to
                                  each hypervisor type.

        Returns:
            None

        Raises:
            RuntimeError: If it is not logged in the guest.
        """
        self._test_logged_in()

        self._logger.debug(
            "performing START HypervisorKVM: guest_name=%s "
            "cpu=%s memory=%s parameters=%s", guest_name, cpu, memory,
            str(parameters))

        virsh = Virsh(self._host_cnn, self._host_session)

        # vm is already running: stop it
        if virsh.is_running(guest_name):
            virsh.destroy(guest_name)

        guest_kvm = GuestKvm(guest_name, cpu, memory,
                             parameters, self._host_session)
        # Activate all hardware
        guest_kvm.activate()

        domain_xml = guest_kvm.to_xml()
        is_netboot = (
            parameters.get("parameters") is not None and
            parameters.get("parameters").get("boot_method") == "network")

        # domain already defined in libvirt: remove it to avoid error when
        # trying to re-define
        if virsh.is_defined(guest_name):
            virsh.undefine(guest_name)

        # network boot: define a temporary domain xml using kernel/initrd
        # to boot
        if is_netboot:
            virsh.define_netboot(
                domain_xml,
                parameters["parameters"]["boot_options"])
        # no netboot: use the final domain xml
        else:
            virsh.define(domain_xml)

        virsh.start(guest_name)

        # netboot performed: re-define domain to remove temporary boot tag
        if is_netboot:
            virsh.define(domain_xml)
            virsh.clean_tmp_dir()
    # start()

    @validate_params
    def reboot(self, guest_name, parameters):
        """
        Reboot a given guest

        Args:
            guest_name (str):  Name of the guest as known by hypervisor.
            parameters (dict): Dictionary with content specific to hypervisor
                               type.

        Returns:
            None

        Raises:
            RuntimeError: In case it is not logged in, or the domain is
                          undefined or not started.
        """
        self._test_logged_in()

        self._logger.debug(
            "performing REBOOT HypervisorKVM: guest_name=%s "
            "parameters=%s", guest_name, str(parameters))

        virsh = Virsh(self._host_cnn, self._host_session)

        if not virsh.is_defined(guest_name):
            raise RuntimeError("Domain {} is not "
                               "defined".format(guest_name))

        if not virsh.is_running(guest_name):
            raise RuntimeError("Domain {} is not "
                               "running".format(guest_name))

        # We cannot use "virsh reset" here since it won't work if we do a
        # network boot. This happens due to the fact that we redefine
        # a running domain (we remove the kernel, initrd, and cmdline tags),
        # and libvirt seems to still use the domain that was used in the start
        # while performing the reset operation.
        virsh.destroy(guest_name)
        virsh.start(guest_name)
    # reboot()

    @validate_params
    def stop(self, guest_name, parameters):
        """
        Stop a given guest

        Args:
            guest_name (str): Name of the guest as known by hypervisor
            parameters (dict): Dictionary with content specific to hypervisor
                               type.

        Returns:
            None

        Raises:
            RuntimeError: In case it is not logged in, or the domain is
                          undefined or not started.
        """
        self._test_logged_in()

        self._logger.debug(
            "performing STOP HypervisorKVM: guest_name=%s "
            "parameters=%s", guest_name, str(parameters))

        virsh = Virsh(self._host_cnn, self._host_session)

        if not virsh.is_defined(guest_name):
            raise RuntimeError("Domain {} is not "
                               "defined".format(guest_name))

        if not virsh.is_running(guest_name):
            raise RuntimeError("Domain {} is not "
                               "running".format(guest_name))

        virsh.destroy(guest_name)
    # stop()
# HypervisorKvm
