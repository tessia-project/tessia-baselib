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
from tessia.baselib.common.logger import get_logger
from tessia.baselib.common.params_validators.utils import validate_params
from tessia.baselib.guests.linux.linux import GuestLinux
from tessia.baselib.hypervisors.base import HypervisorBase
from tessia.baselib.hypervisors.kvm.guest import GuestKvm
from tessia.baselib.hypervisors.kvm.virsh import Virsh

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
    def __init__(self, system_name, host_name, user, passwd, parameters):
        """
        Constructor

        Args:
            system_name (string): string containing the hypervisor name
            host_name (string): hostname or ip address of system
            user (string): user to login to system
            passwd (string): password to login to system
            parameters (dict): a dictionary containing values specific to each
                        hypervisor type

        Raises:
            None
        """
        super().__init__(system_name, host_name, user, passwd, parameters)

        self._logger = get_logger(__name__)

        self._logger.debug(
            "create HypervisorKvm: name='%s' host_name='%s' user='%s' "
            "parameters='%s'",
            self.name,
            self.host_name,
            self.user,
            str(self.parameters)
        )

        # instantiated during login time
        self._host_conn = None
        self._virsh = None
    # __init__()

    def _test_logged_in(self):
        """
        Auxiliary Method. Test if we are logged in the system
        before performing any operation.

        Args:
            None

        Raises:
            RuntimeError: if it is not logged in the system.
        """
        if self._host_conn is None:
            raise RuntimeError("You must login first")
    # _test_logged_in()

    def login(self, timeout=60):
        """
        Execute the login to the hypervisor system using the credentials
        provided.

        Args:
            timeout (int): how many seconds to wait for connection

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

        if self._host_conn is not None:
            self._logger.warning(
                "Login called with connection already active:"
                " dropping previous connection object"
            )

        # a KVM hypervisor is also a linux guest, so we establish connection
        # with it using the GuestLinux class.
        self._host_conn = GuestLinux(
            self.name, self.host_name, self.user, self.passwd, self.parameters)
        self._host_conn.login(timeout)
        self._virsh = Virsh(self._host_conn)
    # login()

    def logoff(self):
        """
        Close an active connection to the hypervisor system

        Args:
            None

        Raises:
            RuntimeError: It is not logged in the guest
        """
        self._test_logged_in()

        self._logger.debug("performing LOGOFF HypervisorKVM")

        self._virsh.close()
        self._virsh = None
        self._host_conn.logoff()
        self._host_conn = None
    # logoff()

    def set_boot_device(self, guest_name, boot_device):
        """
        Set boot device for next load
        For KVM it is a no-op

        Args:
            guest_name (str): guest to operate on
            boot_device (dict): boot device config
        """
        self._logger.debug(
            "performing SET_BOOT_DEVICE HypervisorKvm: name='%s', guest='%s' "
            "boot_device='%s'",
            self.name,
            guest_name,
            str(boot_device)
        )

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

        Raises:
            RuntimeError: If it is not logged in the guest.
        """
        self._test_logged_in()

        self._logger.debug(
            "performing START HypervisorKVM: guest_name=%s "
            "cpu=%s memory=%s parameters=%s", guest_name, cpu, memory,
            str(parameters))

        # vm is already running: stop it
        if self._virsh.is_running(guest_name):
            self._virsh.destroy(guest_name)

        guest_kvm = GuestKvm(guest_name, cpu, memory,
                             parameters, self._host_conn)
        # Activate all hardware
        guest_kvm.activate()

        domain_xml = guest_kvm.to_xml()
        is_netboot = (
            parameters.get("parameters") is not None and
            parameters.get("parameters").get("boot_method") == "network")

        # domain already defined in libvirt: remove it to avoid error when
        # trying to re-define
        if self._virsh.is_defined(guest_name):
            self._virsh.undefine(guest_name)

        # network boot: define a temporary domain xml using kernel/initrd
        # to boot
        if is_netboot:
            self._virsh.define_netboot(
                domain_xml,
                parameters["parameters"]["boot_options"])
        # no netboot: use the final domain xml
        else:
            self._virsh.define(domain_xml)

        self._virsh.start(guest_name)

        # netboot performed: re-define domain to remove temporary boot tag
        if is_netboot:
            self._virsh.define(domain_xml)
            self._virsh.clean_tmp_dir()
    # start()

    @validate_params
    def reboot(self, guest_name, parameters):
        """
        Reboot a given guest

        Args:
            guest_name (str):  Name of the guest as known by hypervisor.
            parameters (dict): Dictionary with content specific to hypervisor
                               type.

        Raises:
            RuntimeError: In case it is not logged in, or the domain is
                          undefined or not started.
        """
        self._test_logged_in()

        self._logger.debug(
            "performing REBOOT HypervisorKVM: guest_name=%s "
            "parameters=%s", guest_name, str(parameters))

        if not self._virsh.is_defined(guest_name):
            raise RuntimeError("Domain {} is not "
                               "defined".format(guest_name))

        if not self._virsh.is_running(guest_name):
            raise RuntimeError("Domain {} is not "
                               "running".format(guest_name))

        # We cannot use "virsh reset" here since it won't work if we do a
        # network boot. This happens due to the fact that we redefine
        # a running domain (we remove the kernel, initrd, and cmdline tags),
        # and libvirt seems to still use the domain that was used in the start
        # while performing the reset operation.
        self._virsh.destroy(guest_name)
        self._virsh.start(guest_name)
    # reboot()

    @validate_params
    def stop(self, guest_name, parameters):
        """
        Stop a given guest

        Args:
            guest_name (str): Name of the guest as known by hypervisor
            parameters (dict): Dictionary with content specific to hypervisor
                               type.

        Raises:
            RuntimeError: In case it is not logged in, or the domain is
                          undefined or not started.
        """
        self._test_logged_in()

        self._logger.debug(
            "performing STOP HypervisorKVM: guest_name=%s "
            "parameters=%s", guest_name, str(parameters))

        if not self._virsh.is_defined(guest_name):
            raise RuntimeError("Domain {} is not "
                               "defined".format(guest_name))

        if not self._virsh.is_running(guest_name):
            raise RuntimeError("Domain {} is not "
                               "running".format(guest_name))

        self._virsh.destroy(guest_name)
    # stop()
# HypervisorKvm
